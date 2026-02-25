from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.models import (db, Invoice, InvoiceItem, Customer, Product, Account,
                             JournalEntry, JournalLine, PaymentReceived, StockMovement,
                             FiscalPeriod, CompanySettings, log_activity)
from datetime import date, timedelta
from decimal import Decimal

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')


def get_next_invoice_number():
    last = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.id.desc()).first()
    num = (int(last.invoice_number.replace('INV-', '')) + 1) if last else 1
    return f'INV-{num:05d}'


def get_next_payment_number():
    last = PaymentReceived.query.filter_by(user_id=current_user.id).order_by(PaymentReceived.id.desc()).first()
    num = (int(last.payment_number.replace('PR-', '')) + 1) if last else 1
    return f'PR-{num:05d}'


def create_invoice_journal_entry(invoice):
    """Create double-entry journal for an invoice (IFRS-compliant with separate tax).
    Service businesses: Revenue only — no COGS, no inventory movement."""
    ar_account = Account.query.filter_by(code='1200', user_id=current_user.id).first()
    sales_account = Account.query.filter_by(code='4000', user_id=current_user.id).first()
    tax_payable_account = Account.query.filter_by(code='2200', user_id=current_user.id).first()

    # Determine business type
    settings = CompanySettings.query.filter_by(user_id=current_user.id).first()
    is_service_biz = settings and settings.business_type == 'service'

    cogs_account = None
    inventory_account = None
    if not is_service_biz:
        cogs_account = Account.query.filter_by(code='5000', user_id=current_user.id).first()
        inventory_account = Account.query.filter_by(code='1300', user_id=current_user.id).first()

    if not ar_account or not sales_account:
        return None

    from routes.journal import get_next_entry_number
    entry = JournalEntry(
        entry_number=get_next_entry_number(),
        date=invoice.date,
        description=f'Invoice {invoice.invoice_number} - {invoice.customer.name}',
        reference=invoice.invoice_number,
        source='sale',
        is_posted=True,
        user_id=current_user.id,
    )

    # Debit: Accounts Receivable (full total including tax)
    entry.lines.append(JournalLine(account_id=ar_account.id, debit=float(invoice.total), credit=0, user_id=current_user.id))

    # Credit: Sales Revenue (subtotal minus discount)
    sales_amount = float(invoice.subtotal) - float(invoice.discount_amount or 0)
    entry.lines.append(JournalLine(account_id=sales_account.id, debit=0, credit=sales_amount, user_id=current_user.id))

    # Credit: Sales Tax Payable (separate tax entry - IAS 12 / VAT compliance)
    tax_amt = float(invoice.tax_amount or 0)
    if tax_amt > 0.001 and tax_payable_account:
        entry.lines.append(JournalLine(account_id=tax_payable_account.id, debit=0, credit=tax_amt, user_id=current_user.id))

    # COGS entries for inventory items (product businesses only)
    if not is_service_biz and cogs_account and inventory_account:
        total_cogs = 0
        for item in invoice.items:
            if item.product and not item.product.is_service:
                cost = float(item.product.cost_price or 0)
                if cost > 0:
                    cogs = float(item.quantity) * cost
                    total_cogs += cogs
        if total_cogs > 0:
            entry.lines.append(JournalLine(account_id=cogs_account.id, debit=total_cogs, credit=0, user_id=current_user.id))
            entry.lines.append(JournalLine(account_id=inventory_account.id, debit=0, credit=total_cogs, user_id=current_user.id))

    db.session.add(entry)
    db.session.flush()
    return entry


@sales_bp.route('/')
@login_required
def index():
    invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.date.desc(), Invoice.id.desc()).all()

    # Auto-update overdue status
    today = date.today()
    for inv in invoices:
        if inv.status in ('owed', 'sent', 'partial') and inv.due_date and inv.due_date < today:
            inv.status = 'overdue'
    db.session.commit()

    return render_template('sales/index.html', invoices=invoices, today=today)


def create_payment_received_journal(payment, customer_name):
    """Create journal entry for a payment received from a customer."""
    ar_account = Account.query.filter_by(code='1200', user_id=current_user.id).first()
    deposit_account = Account.query.filter_by(id=payment.deposit_to_account_id, user_id=current_user.id).first()

    if not ar_account or not deposit_account:
        return None

    from routes.journal import get_next_entry_number
    je = JournalEntry(
        entry_number=get_next_entry_number(),
        date=payment.date,
        description=f'Payment received from {customer_name}',
        reference=payment.payment_number,
        source='sale',
        is_posted=True,
        user_id=current_user.id,
    )
    # Debit Cash/Bank, Credit Accounts Receivable
    je.lines.append(JournalLine(account_id=deposit_account.id, debit=payment.amount, credit=0, user_id=current_user.id))
    je.lines.append(JournalLine(account_id=ar_account.id, debit=0, credit=payment.amount, user_id=current_user.id))
    db.session.add(je)
    db.session.flush()
    return je


def record_stock_out(invoice):
    """Record stock-out movements for all inventory items on an invoice.
    Skipped entirely for service businesses."""
    settings = CompanySettings.query.filter_by(user_id=current_user.id).first()
    if settings and settings.business_type == 'service':
        return  # Service business — no stock movement
    for item in invoice.items:
        if item.product and not item.product.is_service:
            item.product.quantity_on_hand = float(item.product.quantity_on_hand or 0) - float(item.quantity)
            sm = StockMovement(
                product_id=item.product.id,
                date=invoice.date,
                movement_type='out',
                quantity=float(item.quantity),
                unit_cost=float(item.product.cost_price),
                reference=invoice.invoice_number,
                notes=f'Sale to {invoice.customer.name}',
                user_id=current_user.id,
            )
            db.session.add(sm)


def validate_stock_availability(items_data):
    """Check if all inventory items have sufficient stock. Returns list of warning dicts.
    Service businesses always return empty (no stock tracking)."""
    settings = CompanySettings.query.filter_by(user_id=current_user.id).first()
    if settings and settings.business_type == 'service':
        return []  # Service business — no stock validation
    warnings = []
    for item_data in items_data:
        if item_data.get('product_id'):
            product = Product.query.filter_by(id=int(item_data['product_id']), user_id=current_user.id).first()
            if product and not product.is_service:
                qty = float(item_data.get('quantity', 0))
                available = float(product.quantity_on_hand or 0)
                if qty > available:
                    warnings.append({
                        'product': product.name,
                        'requested': qty,
                        'available': available,
                        'short': qty - available,
                    })
    return warnings


@sales_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        payment_choice = request.form.get('payment_choice', 'owe')  # pay_now or owe

        # Period locking check
        inv_date = date.fromisoformat(request.form['date'])
        if FiscalPeriod.is_period_locked(inv_date, current_user.id):
            flash(f'Cannot create invoice in a locked fiscal period ({inv_date.strftime("%B %Y")}).', 'danger')
            return redirect(url_for('sales.create'))

        invoice = Invoice(
            invoice_number=get_next_invoice_number(),
            customer_id=int(request.form['customer_id']),
            date=inv_date,
            due_date=date.fromisoformat(request.form['due_date']) if request.form.get('due_date') else None,
            tax_rate=float(request.form.get('tax_rate', 0) or 0),
            discount_amount=float(request.form.get('discount_amount', 0) or 0),
            notes=request.form.get('notes', ''),
            payment_type=payment_choice,
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

            item = InvoiceItem(
                product_id=int(product_id) if product_id else None,
                description=desc,
                quantity=qty,
                unit_price=price,
                amount=qty * price,
            )
            invoice.items.append(item)

        if not invoice.items:
            flash('At least one line item is required.', 'warning')
        else:
            # Validate stock availability before proceeding
            force_confirm = request.form.get('force_confirm') == '1'
            stock_warnings = validate_stock_availability([
                {'product_id': item.product_id, 'quantity': item.quantity}
                for item in invoice.items if item.product_id
            ])
            if stock_warnings and not force_confirm:
                for w in stock_warnings:
                    flash(f'Insufficient stock: {w["product"]}: requested {w["requested"]} but only {w["available"]} available', 'danger')
                customers = Customer.query.filter_by(is_active=True, user_id=current_user.id).order_by(Customer.name).all()
                products = Product.query.filter_by(is_active=True, user_id=current_user.id).order_by(Product.name).all()
                bank_accounts = Account.query.filter(
                    Account.account_type == 'Asset',
                    Account.sub_type.in_(['Current Asset']),
                    Account.user_id == current_user.id
                ).order_by(Account.code).all()
                return render_template('sales/form.html', invoice=None, customers=customers,
                                       products=products, bank_accounts=bank_accounts,
                                       today=date.today(),
                                       due_default=(date.today() + timedelta(days=30)).isoformat())

            invoice.recalculate()

            # Add to session so relationships resolve (e.g. invoice.customer)
            db.session.add(invoice)
            db.session.flush()

            # Always: create sale journal entry
            invoice.status = 'sent'
            je = create_invoice_journal_entry(invoice)
            if je:
                invoice.journal_entry_id = je.id

            # Warn if inventory products have zero cost price (COGS won't be recorded)
            zero_cost_items = [item for item in invoice.items
                               if item.product and not item.product.is_service
                               and float(item.product.cost_price or 0) == 0]
            if zero_cost_items:
                names = ', '.join(item.product.name for item in zero_cost_items)
                flash(f'⚠️ Warning: {names} — cost price is $0, so COGS was not recorded. '
                      f'Update the cost price in Inventory to fix future invoices.', 'warning')

            # Always: record stock-out for inventory items
            record_stock_out(invoice)

            # Update customer balance (they owe us)
            customer = Customer.query.filter_by(id=invoice.customer_id, user_id=current_user.id).first()
            if customer:
                customer.balance += invoice.total

            if payment_choice == 'pay_now':
                # ── PAY NOW: create immediate payment ──
                deposit_to_account_id = request.form.get('deposit_to_account_id')
                payment_method = request.form.get('payment_method', 'cash')

                if not deposit_to_account_id:
                    flash('Please select a deposit account for Pay Now.', 'warning')
                    customers = Customer.query.filter_by(is_active=True, user_id=current_user.id).order_by(Customer.name).all()
                    products = Product.query.filter_by(is_active=True, user_id=current_user.id).order_by(Product.name).all()
                    bank_accounts = Account.query.filter(
                        Account.account_type == 'Asset',
                        Account.sub_type.in_(['Current Asset']),
                        Account.user_id == current_user.id
                    ).order_by(Account.code).all()
                    return render_template('sales/form.html', invoice=None, customers=customers,
                                           products=products, bank_accounts=bank_accounts,
                                           today=date.today(),
                                           due_default=(date.today() + timedelta(days=30)).isoformat())

                payment = PaymentReceived(
                    payment_number=get_next_payment_number(),
                    customer_id=invoice.customer_id,
                    invoice_id=invoice.id,
                    date=invoice.date,
                    amount=invoice.total,
                    payment_method=payment_method,
                    reference=f'Cash sale for {invoice.invoice_number}',
                    deposit_to_account_id=int(deposit_to_account_id),
                    notes=f'Immediate payment for {invoice.invoice_number}',
                    user_id=current_user.id,
                )

                pje = create_payment_received_journal(payment, invoice.customer.name)
                if pje:
                    payment.journal_entry_id = pje.id

                db.session.add(payment)

                # Mark invoice as paid
                invoice.amount_paid = invoice.total
                invoice.balance_due = 0
                invoice.status = 'paid'
                invoice.paid_date = invoice.date

                # Customer balance back to 0 (payment offsets)
                if customer:
                    customer.balance -= invoice.total

                db.session.commit()
                flash(f'Invoice {invoice.invoice_number} created and PAID immediately. Stock updated.', 'success')
                log_activity('create', 'Invoice', invoice.id, invoice.invoice_number,
                             f'Cash sale {invoice.invoice_number} to {invoice.customer.name} for {invoice.total:,.2f}')
                db.session.commit()
                return redirect(url_for('sales.view', id=invoice.id))

            else:
                # ── OWE: save as owed with due date ──
                if not invoice.due_date:
                    invoice.due_date = invoice.date + timedelta(days=30)
                invoice.status = 'owed'

                db.session.commit()
                flash(f'Invoice {invoice.invoice_number} created as OWED. Due: {invoice.due_date.strftime("%b %d, %Y")}. Stock updated.', 'success')
                log_activity('create', 'Invoice', invoice.id, invoice.invoice_number,
                             f'Credit sale {invoice.invoice_number} to {invoice.customer.name} for {invoice.total:,.2f}')
                db.session.commit()
                return redirect(url_for('sales.view', id=invoice.id))

    customers = Customer.query.filter_by(is_active=True, user_id=current_user.id).order_by(Customer.name).all()
    products = Product.query.filter_by(is_active=True, user_id=current_user.id).order_by(Product.name).all()
    bank_accounts = Account.query.filter(
        Account.account_type == 'Asset',
        Account.sub_type.in_(['Current Asset']),
        Account.user_id == current_user.id
    ).order_by(Account.code).all()
    return render_template('sales/form.html', invoice=None, customers=customers,
                           products=products, bank_accounts=bank_accounts,
                           today=date.today(),
                           due_default=(date.today() + timedelta(days=30)).isoformat())


@sales_bp.route('/view/<int:id>')
@login_required
def view(id):
    invoice = Invoice.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    # Auto-update overdue
    if invoice.status in ('owed', 'sent', 'partial') and invoice.due_date and invoice.due_date < date.today():
        invoice.status = 'overdue'
        db.session.commit()
    return render_template('sales/view.html', invoice=invoice, today=date.today())


@sales_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    invoice = Invoice.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if invoice.status != 'draft':
        flash('Only draft invoices can be deleted.', 'warning')
        return redirect(url_for('sales.index'))
    log_activity('delete', 'Invoice', invoice.id, invoice.invoice_number,
                 f'Deleted invoice {invoice.invoice_number}')
    db.session.delete(invoice)
    db.session.commit()
    flash('Invoice deleted.', 'success')
    return redirect(url_for('sales.index'))


# ─── PAYMENTS RECEIVED ────────────────────────────────────
@sales_bp.route('/payments')
@login_required
def payments():
    all_payments = PaymentReceived.query.filter_by(user_id=current_user.id).order_by(PaymentReceived.date.desc()).all()
    return render_template('sales/payments.html', payments=all_payments)


@sales_bp.route('/payments/create', methods=['GET', 'POST'])
@login_required
def create_payment():
    if request.method == 'POST':
        invoice_id = request.form.get('invoice_id') or None
        customer_id = int(request.form['customer_id'])
        amount = float(request.form['amount'])

        payment = PaymentReceived(
            payment_number=get_next_payment_number(),
            customer_id=customer_id,
            invoice_id=int(invoice_id) if invoice_id else None,
            date=date.fromisoformat(request.form['date']),
            amount=amount,
            payment_method=request.form.get('payment_method', 'cash'),
            reference=request.form.get('reference', ''),
            deposit_to_account_id=int(request.form['deposit_to_account_id']),
            notes=request.form.get('notes', ''),
            user_id=current_user.id,
        )

        # Create journal entry
        ar_account = Account.query.filter_by(code='1200', user_id=current_user.id).first()
        deposit_account = Account.query.filter_by(id=payment.deposit_to_account_id, user_id=current_user.id).first()

        if ar_account and deposit_account:
            from routes.journal import get_next_entry_number
            je = JournalEntry(
                entry_number=get_next_entry_number(),
                date=payment.date,
                description=f'Payment received from {Customer.query.filter_by(id=customer_id, user_id=current_user.id).first().name}',
                reference=payment.payment_number,
                source='sale',
                is_posted=True,
                user_id=current_user.id,
            )
            je.lines.append(JournalLine(account_id=deposit_account.id, debit=amount, credit=0, user_id=current_user.id))
            je.lines.append(JournalLine(account_id=ar_account.id, debit=0, credit=amount, user_id=current_user.id))
            db.session.add(je)
            db.session.flush()
            payment.journal_entry_id = je.id

        # Update invoice
        invoice = None
        if invoice_id:
            invoice = Invoice.query.filter_by(id=int(invoice_id), user_id=current_user.id).first()
            if invoice:
                invoice.amount_paid += amount
                invoice.balance_due = invoice.total - invoice.amount_paid
                if invoice.balance_due <= 0.01:
                    invoice.status = 'paid'
                    invoice.paid_date = payment.date
                    invoice.balance_due = 0
                else:
                    invoice.status = 'partial'

        # Update customer balance
        customer = Customer.query.filter_by(id=customer_id, user_id=current_user.id).first()
        if customer:
            customer.balance -= amount

        db.session.add(payment)
        db.session.commit()

        log_activity('create', 'Payment Received', payment.id, payment.payment_number,
                     f'Payment {payment.payment_number} of {amount:,.2f} from {customer.name if customer else "customer"}')
        db.session.commit()

        if invoice_id and invoice and invoice.status == 'paid':
            flash(f'Payment {payment.payment_number} recorded. Invoice {invoice.invoice_number} is now FULLY PAID!', 'success')
        else:
            flash(f'Payment {payment.payment_number} recorded.', 'success')

        if invoice_id:
            return redirect(url_for('sales.view', id=int(invoice_id)))
        return redirect(url_for('sales.payments'))

    customers = Customer.query.filter_by(is_active=True, user_id=current_user.id).order_by(Customer.name).all()
    invoices = Invoice.query.filter(Invoice.status.in_(['sent', 'owed', 'partial', 'overdue']), Invoice.user_id == current_user.id).order_by(Invoice.date.desc()).all()
    bank_accounts = Account.query.filter(Account.account_type == 'Asset',
                                          Account.sub_type.in_(['Current Asset']),
                                          Account.user_id == current_user.id).order_by(Account.code).all()

    # Pre-fill if coming from an invoice
    prefill_invoice = None
    if request.args.get('invoice_id'):
        prefill_invoice = Invoice.query.filter_by(id=int(request.args.get('invoice_id')), user_id=current_user.id).first()

    return render_template('sales/payment_form.html', payment=None, customers=customers,
                           invoices=invoices, bank_accounts=bank_accounts, today=date.today(),
                           prefill_invoice=prefill_invoice)
