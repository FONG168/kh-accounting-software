from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.models import (db, DebitNote, DebitNoteItem, Bill, Vendor, Product,
                             Account, JournalEntry, JournalLine, StockMovement,
                             FiscalPeriod, log_activity)
from datetime import date
from decimal import Decimal

debit_notes_bp = Blueprint('debit_notes', __name__, url_prefix='/debit-notes')


def get_next_dn_number():
    last = DebitNote.query.filter_by(user_id=current_user.id).order_by(DebitNote.id.desc()).first()
    num = (int(last.debit_note_number.replace('DN-', '')) + 1) if last else 1
    return f'DN-{num:05d}'


def create_dn_journal_entry(dn):
    """Create journal entry for debit note (reversal of purchase).
    Debit Accounts Payable (reduce liability), Credit Inventory/Expense.
    If tax, also Credit Sales Tax Payable (reverse input tax credit).
    """
    ap_account = Account.query.filter_by(code='2000', user_id=current_user.id).first()
    inventory_account = Account.query.filter_by(code='1300', user_id=current_user.id).first()
    expense_account = Account.query.filter_by(code='5000', user_id=current_user.id).first()
    tax_payable_account = Account.query.filter_by(code='2200', user_id=current_user.id).first()

    if not ap_account:
        return None

    from routes.journal import get_next_entry_number
    entry = JournalEntry(
        entry_number=get_next_entry_number(),
        date=dn.date,
        description=f'Debit Note {dn.debit_note_number} - {dn.vendor.name}',
        reference=dn.debit_note_number,
        source='debit_note',
        is_posted=True,
        user_id=current_user.id,
    )

    # Debit: Accounts Payable (reduce what we owe)
    entry.lines.append(JournalLine(account_id=ap_account.id,
                                   debit=float(dn.total), credit=0, user_id=current_user.id))

    # Credit: Inventory or Expense (reduce asset/expense)
    inv_total = 0
    exp_total = 0
    for item in dn.items:
        if item.product and not item.product.is_service:
            inv_total += float(item.amount or 0)
        else:
            exp_total += float(item.amount or 0)

    if inv_total > 0 and inventory_account:
        entry.lines.append(JournalLine(account_id=inventory_account.id,
                                       debit=0, credit=inv_total, user_id=current_user.id))
    if exp_total > 0 and expense_account:
        entry.lines.append(JournalLine(account_id=expense_account.id,
                                       debit=0, credit=exp_total, user_id=current_user.id))
    if inv_total == 0 and exp_total == 0:
        target = expense_account or inventory_account
        if target:
            entry.lines.append(JournalLine(account_id=target.id,
                                           debit=0, credit=float(dn.subtotal), user_id=current_user.id))

    # Credit: Sales Tax Payable (reverse input tax credit)
    tax_amt = float(dn.tax_amount or 0)
    if tax_amt > 0.001 and tax_payable_account:
        entry.lines.append(JournalLine(account_id=tax_payable_account.id,
                                       debit=0, credit=tax_amt, user_id=current_user.id))

    db.session.add(entry)
    db.session.flush()
    return entry


@debit_notes_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 25
    pagination = DebitNote.query.filter_by(user_id=current_user.id).order_by(
        DebitNote.date.desc(), DebitNote.id.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('debit_notes/index.html',
                           debit_notes=pagination.items, pagination=pagination)


@debit_notes_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        dn_date = date.fromisoformat(request.form['date'])

        if FiscalPeriod.is_period_locked(dn_date, current_user.id):
            flash(f'Cannot create debit note in a locked period ({dn_date.strftime("%B %Y")}).', 'danger')
            vendors = Vendor.query.filter_by(is_active=True, user_id=current_user.id).order_by(Vendor.name).all()
            products = Product.query.filter_by(is_active=True, user_id=current_user.id).order_by(Product.name).all()
            bills = Bill.query.filter_by(user_id=current_user.id).order_by(Bill.id.desc()).all()
            return render_template('debit_notes/form.html', dn=None, vendors=vendors,
                                   products=products, bills=bills, today=date.today())

        bill_id = request.form.get('bill_id') or None
        dn = DebitNote(
            debit_note_number=get_next_dn_number(),
            bill_id=int(bill_id) if bill_id else None,
            vendor_id=int(request.form['vendor_id']),
            date=dn_date,
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

            item = DebitNoteItem(
                product_id=int(product_id) if product_id else None,
                description=desc,
                quantity=qty,
                unit_price=price,
                amount=qty * price,
            )
            dn.items.append(item)

        if not dn.items:
            flash('At least one line item is required.', 'warning')
        else:
            dn.subtotal = sum(float(item.amount) for item in dn.items)
            tax_rate = float(request.form.get('tax_rate', 0) or 0)
            dn.tax_amount = round(dn.subtotal * tax_rate / 100, 2)
            dn.total = dn.subtotal + dn.tax_amount
            dn.status = 'applied'

            db.session.add(dn)
            db.session.flush()

            je = create_dn_journal_entry(dn)
            if je:
                dn.journal_entry_id = je.id

            # Return stock for inventory items
            for item in dn.items:
                if item.product and not item.product.is_service:
                    item.product.quantity_on_hand -= item.quantity
                    sm = StockMovement(
                        product_id=item.product.id,
                        date=dn.date,
                        movement_type='out',
                        quantity=item.quantity,
                        unit_cost=item.unit_price,
                        reference=dn.debit_note_number,
                        notes=f'Purchase return - Debit Note {dn.debit_note_number}',
                        user_id=current_user.id,
                    )
                    db.session.add(sm)

            # Reduce vendor balance
            vendor = Vendor.query.filter_by(id=dn.vendor_id, user_id=current_user.id).first()
            if vendor:
                vendor.balance -= float(dn.total)

            # If linked to bill, update bill balance
            if dn.bill_id:
                bill = Bill.query.filter_by(id=dn.bill_id, user_id=current_user.id).first()
                if bill:
                    bill.amount_paid = float(bill.amount_paid or 0) + float(dn.total)
                    bill.balance_due = float(bill.total) - float(bill.amount_paid)
                    if float(bill.balance_due) <= 0.01:
                        bill.status = 'paid'
                    else:
                        bill.status = 'partial'

            db.session.flush()
            log_activity('create', 'Debit Note', dn.id, dn.debit_note_number,
                         f'Created debit note {dn.debit_note_number} for {dn.vendor.name}')
            db.session.commit()
            flash(f'Debit note {dn.debit_note_number} created.', 'success')
            return redirect(url_for('debit_notes.index'))

    vendors = Vendor.query.filter_by(is_active=True, user_id=current_user.id).order_by(Vendor.name).all()
    products_raw = Product.query.filter_by(is_active=True, user_id=current_user.id).order_by(Product.name).all()
    products = [{'id': p.id, 'name': p.name, 'selling_price': float(p.selling_price or 0)} for p in products_raw]
    bills = Bill.query.filter_by(user_id=current_user.id).order_by(Bill.id.desc()).all()
    return render_template('debit_notes/form.html', dn=None, vendors=vendors,
                           products=products, bills=bills, today=date.today())


@debit_notes_bp.route('/view/<int:id>')
@login_required
def view(id):
    dn = DebitNote.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return render_template('debit_notes/view.html', dn=dn)


@debit_notes_bp.route('/void/<int:id>', methods=['POST'])
@login_required
def void(id):
    dn = DebitNote.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if dn.status == 'void':
        flash('Debit note is already voided.', 'warning')
        return redirect(url_for('debit_notes.index'))

    dn.status = 'void'
    log_activity('update', 'Debit Note', dn.id, dn.debit_note_number,
                 f'Voided debit note {dn.debit_note_number}')
    db.session.commit()
    flash(f'Debit note {dn.debit_note_number} has been voided.', 'success')
    return redirect(url_for('debit_notes.index'))
