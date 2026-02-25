from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.models import (db, CreditNote, CreditNoteItem, Invoice, Customer, Product,
                             Account, JournalEntry, JournalLine, StockMovement,
                             FiscalPeriod, log_activity)
from datetime import date
from decimal import Decimal

credit_notes_bp = Blueprint('credit_notes', __name__, url_prefix='/credit-notes')


def get_next_cn_number():
    last = CreditNote.query.filter_by(user_id=current_user.id).order_by(CreditNote.id.desc()).first()
    num = (int(last.credit_note_number.replace('CN-', '')) + 1) if last else 1
    return f'CN-{num:05d}'


def create_cn_journal_entry(cn):
    """Create journal entry for credit note (reversal of sale).
    Debit Sales Revenue, Credit Accounts Receivable.
    If tax, also Debit Sales Tax Payable.
    """
    ar_account = Account.query.filter_by(code='1200', user_id=current_user.id).first()
    sales_account = Account.query.filter_by(code='4000', user_id=current_user.id).first()
    tax_payable_account = Account.query.filter_by(code='2200', user_id=current_user.id).first()

    if not ar_account or not sales_account:
        return None

    from routes.journal import get_next_entry_number
    entry = JournalEntry(
        entry_number=get_next_entry_number(),
        date=cn.date,
        description=f'Credit Note {cn.credit_note_number} - {cn.customer.name}',
        reference=cn.credit_note_number,
        source='credit_note',
        is_posted=True,
        user_id=current_user.id,
    )

    # Debit: Sales Revenue (reduce revenue)
    entry.lines.append(JournalLine(account_id=sales_account.id,
                                   debit=float(cn.subtotal), credit=0, user_id=current_user.id))

    # Debit: Sales Tax Payable (reduce tax liability)
    tax_amt = float(cn.tax_amount or 0)
    if tax_amt > 0.001 and tax_payable_account:
        entry.lines.append(JournalLine(account_id=tax_payable_account.id,
                                       debit=tax_amt, credit=0, user_id=current_user.id))

    # Credit: Accounts Receivable (reduce amount owed by customer)
    entry.lines.append(JournalLine(account_id=ar_account.id,
                                   debit=0, credit=float(cn.total), user_id=current_user.id))

    db.session.add(entry)
    db.session.flush()
    return entry


@credit_notes_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 25
    pagination = CreditNote.query.filter_by(user_id=current_user.id).order_by(
        CreditNote.date.desc(), CreditNote.id.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('credit_notes/index.html',
                           credit_notes=pagination.items, pagination=pagination)


@credit_notes_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        cn_date = date.fromisoformat(request.form['date'])

        if FiscalPeriod.is_period_locked(cn_date, current_user.id):
            flash(f'Cannot create credit note in a locked period ({cn_date.strftime("%B %Y")}).', 'danger')
            customers = Customer.query.filter_by(is_active=True, user_id=current_user.id).order_by(Customer.name).all()
            products = Product.query.filter_by(is_active=True, user_id=current_user.id).order_by(Product.name).all()
            invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.id.desc()).all()
            return render_template('credit_notes/form.html', cn=None, customers=customers,
                                   products=products, invoices=invoices, today=date.today())

        invoice_id = request.form.get('invoice_id') or None
        cn = CreditNote(
            credit_note_number=get_next_cn_number(),
            invoice_id=int(invoice_id) if invoice_id else None,
            customer_id=int(request.form['customer_id']),
            date=cn_date,
            reason=request.form.get('reason', ''),
            user_id=current_user.id,
        )

        item_count = int(request.form.get('item_count', 0))
        for i in range(item_count):
            desc = request.form.get(f'items-{i}-description', '')
            if not desc:
                continue
            qty = float(request.form.get(f'items-{i}-quantity', 1) or 1)
            price = float(request.form.get(f'items-{i}-unit_price', 0) or 0)
            product_id = request.form.get(f'items-{i}-product_id') or None

            item = CreditNoteItem(
                product_id=int(product_id) if product_id else None,
                description=desc,
                quantity=qty,
                unit_price=price,
                amount=qty * price,
            )
            cn.items.append(item)

        if not cn.items:
            flash('At least one line item is required.', 'warning')
        else:
            # Calculate totals
            cn.subtotal = sum(float(item.amount) for item in cn.items)
            # Apply tax from linked invoice's rate, or from form
            tax_rate = float(request.form.get('tax_rate', 0) or 0)
            cn.tax_amount = round(cn.subtotal * tax_rate / 100, 2)
            cn.total = cn.subtotal + cn.tax_amount
            cn.status = 'applied'

            db.session.add(cn)
            db.session.flush()

            # Journal entry
            je = create_cn_journal_entry(cn)
            if je:
                cn.journal_entry_id = je.id

            # Return stock for inventory items
            for item in cn.items:
                if item.product and not item.product.is_service:
                    item.product.quantity_on_hand += item.quantity
                    sm = StockMovement(
                        product_id=item.product.id,
                        date=cn.date,
                        movement_type='in',
                        quantity=item.quantity,
                        unit_cost=item.unit_price,
                        reference=cn.credit_note_number,
                        notes=f'Sales return - Credit Note {cn.credit_note_number}',
                        user_id=current_user.id,
                    )
                    db.session.add(sm)

            # Reduce customer balance
            customer = Customer.query.filter_by(id=cn.customer_id, user_id=current_user.id).first()
            if customer:
                customer.balance -= float(cn.total)

            # If linked to invoice, update invoice balance
            if cn.invoice_id:
                invoice = Invoice.query.filter_by(id=cn.invoice_id, user_id=current_user.id).first()
                if invoice:
                    invoice.amount_paid = float(invoice.amount_paid or 0) + float(cn.total)
                    invoice.balance_due = float(invoice.total) - float(invoice.amount_paid)
                    if float(invoice.balance_due) <= 0.01:
                        invoice.status = 'paid'
                    else:
                        invoice.status = 'partial'

            db.session.commit()
            log_activity('create', 'Credit Note', cn.id, cn.credit_note_number,
                         f'Created credit note {cn.credit_note_number} for {cn.customer.name}')
            db.session.commit()
            flash(f'Credit note {cn.credit_note_number} created.', 'success')
            return redirect(url_for('credit_notes.index'))

    customers = Customer.query.filter_by(is_active=True, user_id=current_user.id).order_by(Customer.name).all()
    products = Product.query.filter_by(is_active=True, user_id=current_user.id).order_by(Product.name).all()
    invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.id.desc()).all()
    return render_template('credit_notes/form.html', cn=None, customers=customers,
                           products=products, invoices=invoices, today=date.today())


@credit_notes_bp.route('/view/<int:id>')
@login_required
def view(id):
    cn = CreditNote.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return render_template('credit_notes/view.html', cn=cn)


@credit_notes_bp.route('/void/<int:id>', methods=['POST'])
@login_required
def void(id):
    cn = CreditNote.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if cn.status == 'void':
        flash('Credit note is already voided.', 'warning')
        return redirect(url_for('credit_notes.index'))

    cn.status = 'void'
    log_activity('update', 'Credit Note', cn.id, cn.credit_note_number,
                 f'Voided credit note {cn.credit_note_number}')
    db.session.commit()
    flash(f'Credit note {cn.credit_note_number} has been voided.', 'success')
    return redirect(url_for('credit_notes.index'))
