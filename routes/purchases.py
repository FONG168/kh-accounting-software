from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.models import (db, Bill, BillItem, Vendor, Product, Account,
                             JournalEntry, JournalLine, PaymentMade, StockMovement,
                             FiscalPeriod, CompanySettings, log_activity)
from datetime import date, timedelta
from decimal import Decimal

purchases_bp = Blueprint('purchases', __name__, url_prefix='/purchases')


def get_next_bill_number():
    last = Bill.query.filter_by(user_id=current_user.id).order_by(Bill.id.desc()).first()
    num = (int(last.bill_number.replace('BILL-', '')) + 1) if last else 1
    return f'BILL-{num:05d}'


def get_next_payment_made_number():
    last = PaymentMade.query.filter_by(user_id=current_user.id).order_by(PaymentMade.id.desc()).first()
    num = (int(last.payment_number.replace('PM-', '')) + 1) if last else 1
    return f'PM-{num:05d}'


def create_bill_journal_entry(bill):
    """Create double-entry journal for a bill (purchase) - IFRS-compliant with separate tax."""
    ap_account = Account.query.filter_by(code='2000', user_id=current_user.id).first()
    inventory_account = Account.query.filter_by(code='1300', user_id=current_user.id).first()
    expense_account = Account.query.filter_by(code='5000', user_id=current_user.id).first()
    tax_payable_account = Account.query.filter_by(code='2200', user_id=current_user.id).first()

    if not ap_account:
        return None

    from routes.journal import get_next_entry_number
    entry = JournalEntry(
        entry_number=get_next_entry_number(),
        date=bill.date,
        description=f'Bill {bill.bill_number} - {bill.vendor.name}',
        reference=bill.bill_number,
        source='purchase',
        is_posted=True,
        user_id=current_user.id,
    )

    # For inventory items: Debit Inventory, for non-inventory: Debit Expense
    inv_total = 0
    exp_total = 0
    for item in bill.items:
        if item.product and not item.product.is_service:
            inv_total += float(item.amount or 0)
        else:
            exp_total += float(item.amount or 0)

    if inv_total > 0 and inventory_account:
        entry.lines.append(JournalLine(account_id=inventory_account.id, debit=inv_total, credit=0, user_id=current_user.id))
    if exp_total > 0 and expense_account:
        entry.lines.append(JournalLine(account_id=expense_account.id, debit=exp_total, credit=0, user_id=current_user.id))
    if inv_total == 0 and exp_total == 0:
        entry.lines.append(JournalLine(account_id=expense_account.id if expense_account else ap_account.id,
                                        debit=float(bill.subtotal or 0), credit=0, user_id=current_user.id))

    # Debit: Input Tax (reduces Sales Tax Payable - IAS 12 / VAT input credit)
    tax_amt = float(bill.tax_amount or 0)
    if tax_amt > 0.001 and tax_payable_account:
        entry.lines.append(JournalLine(account_id=tax_payable_account.id, debit=tax_amt, credit=0, user_id=current_user.id))

    # Credit: Accounts Payable (full total including tax)
    entry.lines.append(JournalLine(account_id=ap_account.id, debit=0, credit=float(bill.total), user_id=current_user.id))

    db.session.add(entry)
    db.session.flush()
    return entry


def create_payment_journal(payment, vendor_name):
    """Create journal entry for a payment made to a vendor."""
    ap_account = Account.query.filter_by(code='2000', user_id=current_user.id).first()
    paid_from = Account.query.filter_by(id=payment.paid_from_account_id, user_id=current_user.id).first()

    if not ap_account or not paid_from:
        return None

    from routes.journal import get_next_entry_number
    je = JournalEntry(
        entry_number=get_next_entry_number(),
        date=payment.date,
        description=f'Payment to {vendor_name}',
        reference=payment.payment_number,
        source='purchase',
        is_posted=True,
        user_id=current_user.id,
    )
    # Debit AP (reduce liability), Credit Cash/Bank
    je.lines.append(JournalLine(account_id=ap_account.id, debit=payment.amount, credit=0, user_id=current_user.id))
    je.lines.append(JournalLine(account_id=paid_from.id, debit=0, credit=payment.amount, user_id=current_user.id))
    db.session.add(je)
    db.session.flush()
    return je


def record_stock_in(bill):
    """Record stock-in movements for all inventory items on a bill.
    Skipped for service businesses."""
    settings = CompanySettings.query.filter_by(user_id=current_user.id).first()
    if settings and settings.business_type == 'service':
        return  # Service business — no stock movement
    for item in bill.items:
        if item.product and not item.product.is_service:
            item.product.quantity_on_hand = float(item.product.quantity_on_hand or 0) + float(item.quantity)
            item.product.cost_price = item.unit_cost  # update latest cost
            sm = StockMovement(
                product_id=item.product.id,
                date=bill.date,
                movement_type='in',
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                reference=bill.bill_number,
                notes=f'Purchase from {bill.vendor.name}',
                user_id=current_user.id,
            )
            db.session.add(sm)


@purchases_bp.route('/')
@login_required
def index():
    bills = Bill.query.filter_by(user_id=current_user.id).order_by(Bill.date.desc(), Bill.id.desc()).all()

    # Auto-update overdue status
    today = date.today()
    for bill in bills:
        if bill.status in ('owed', 'received', 'partial') and bill.due_date and bill.due_date < today:
            bill.status = 'overdue'
    db.session.commit()

    return render_template('purchases/index.html', bills=bills, today=today)


@purchases_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        bill_date = date.fromisoformat(request.form['date'])

        # Period locking check
        if FiscalPeriod.is_period_locked(bill_date, current_user.id):
            flash(f'Cannot create bill in a locked fiscal period ({bill_date.strftime("%B %Y")}).', 'danger')
            vendors = Vendor.query.filter_by(is_active=True, user_id=current_user.id).order_by(Vendor.name).all()
            products = Product.query.filter_by(is_active=True, user_id=current_user.id).order_by(Product.name).all()
            bank_accounts = Account.query.filter(
                Account.account_type == 'Asset',
                Account.sub_type.in_(['Current Asset']),
                Account.user_id == current_user.id
            ).order_by(Account.code).all()
            return render_template('purchases/form.html', bill=None, vendors=vendors,
                                   products=products, bank_accounts=bank_accounts, today=date.today())

        payment_choice = request.form.get('payment_choice', 'owe')  # pay_now or owe

        bill = Bill(
            bill_number=get_next_bill_number(),
            vendor_id=int(request.form['vendor_id']),
            date=bill_date,
            due_date=date.fromisoformat(request.form['due_date']) if request.form.get('due_date') else None,
            tax_rate=float(request.form.get('tax_rate', 0) or 0),
            notes=request.form.get('notes', ''),
            payment_type=payment_choice,
            user_id=current_user.id,
        )

        # Parse line items
        item_count = int(request.form.get('item_count', 0))
        for i in range(item_count):
            desc = request.form.get(f'items-{i}-description', '')
            if not desc:
                continue
            qty = float(request.form.get(f'items-{i}-quantity', 1) or 1)
            cost = float(request.form.get(f'items-{i}-unit_price', 0) or 0)
            product_id = request.form.get(f'items-{i}-product_id') or None

            item = BillItem(
                product_id=int(product_id) if product_id else None,
                description=desc,
                quantity=qty,
                unit_cost=cost,
                amount=qty * cost,
            )
            bill.items.append(item)

        if not bill.items:
            flash('At least one line item is required.', 'warning')
        else:
            bill.recalculate()

            # Add bill to session first so we can access relationships
            db.session.add(bill)
            db.session.flush()

            # Always: create journal entry + record stock
            je = create_bill_journal_entry(bill)
            if je:
                bill.journal_entry_id = je.id

            # Always: record stock-in for inventory items
            record_stock_in(bill)

            # Update vendor balance (they owe us nothing, we owe them)
            vendor = Vendor.query.filter_by(id=bill.vendor_id, user_id=current_user.id).first()
            if vendor:
                vendor.balance += bill.total

            if payment_choice == 'pay_now':
                # ── PAY NOW: create immediate payment ──
                paid_from_account_id = request.form.get('paid_from_account_id')
                payment_method = request.form.get('payment_method', 'cash')

                if not paid_from_account_id:
                    flash('Please select a payment account.', 'warning')
                    vendors = Vendor.query.filter_by(is_active=True, user_id=current_user.id).order_by(Vendor.name).all()
                    products = Product.query.filter_by(is_active=True, user_id=current_user.id).order_by(Product.name).all()
                    bank_accounts = Account.query.filter(
                        Account.account_type == 'Asset',
                        Account.sub_type.in_(['Current Asset']),
                        Account.user_id == current_user.id
                    ).order_by(Account.code).all()
                    return render_template('purchases/form.html', bill=None, vendors=vendors,
                                           products=products, bank_accounts=bank_accounts,
                                           today=date.today(),
                                           due_default=(date.today() + timedelta(days=30)).isoformat())

                db.session.flush()  # ensure bill.id is available for payment

                payment = PaymentMade(
                    payment_number=get_next_payment_made_number(),
                    vendor_id=bill.vendor_id,
                    bill_id=bill.id,
                    date=bill.date,
                    amount=bill.total,
                    payment_method=payment_method,
                    reference=f'Pay-on-purchase for {bill.bill_number}',
                    paid_from_account_id=int(paid_from_account_id),
                    notes=f'Immediate payment for {bill.bill_number}',
                    user_id=current_user.id,
                )

                pje = create_payment_journal(payment, bill.vendor.name)
                if pje:
                    payment.journal_entry_id = pje.id

                db.session.add(payment)

                # Mark bill as paid
                bill.amount_paid = bill.total
                bill.balance_due = 0
                bill.status = 'paid'
                bill.paid_date = bill.date

                # Update vendor balance (payment reduces it)
                if vendor:
                    vendor.balance -= bill.total

                db.session.commit()
                flash(f'Bill {bill.bill_number} created and PAID immediately. Stock updated.', 'success')
                log_activity('create', 'Bill', bill.id, bill.bill_number,
                             f'Cash purchase {bill.bill_number} from {bill.vendor.name} for {bill.total:,.2f}')
                db.session.commit()
                return redirect(url_for('purchases.view', id=bill.id))

            else:
                # ── OWE: save as owed with due date ──
                if not bill.due_date:
                    bill.due_date = bill.date + timedelta(days=30)
                bill.status = 'owed'

                db.session.commit()
                flash(f'Bill {bill.bill_number} created as OWED. Due: {bill.due_date.strftime("%b %d, %Y")}. Stock updated.', 'success')
                log_activity('create', 'Bill', bill.id, bill.bill_number,
                             f'Credit purchase {bill.bill_number} from {bill.vendor.name} for {bill.total:,.2f}')
                db.session.commit()
                return redirect(url_for('purchases.view', id=bill.id))

    vendors = Vendor.query.filter_by(is_active=True, user_id=current_user.id).order_by(Vendor.name).all()
    products = Product.query.filter_by(is_active=True, user_id=current_user.id).order_by(Product.name).all()
    bank_accounts = Account.query.filter(
        Account.account_type == 'Asset',
        Account.sub_type.in_(['Current Asset']),
        Account.user_id == current_user.id
    ).order_by(Account.code).all()
    return render_template('purchases/form.html', bill=None, vendors=vendors,
                           products=products, bank_accounts=bank_accounts,
                           today=date.today(),
                           due_default=(date.today() + timedelta(days=30)).isoformat())


@purchases_bp.route('/view/<int:id>')
@login_required
def view(id):
    bill = Bill.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    # Auto-update overdue
    if bill.status in ('owed', 'received', 'partial') and bill.due_date and bill.due_date < date.today():
        bill.status = 'overdue'
        db.session.commit()
    return render_template('purchases/view.html', bill=bill, today=date.today())


@purchases_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    bill = Bill.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if bill.status not in ('draft',):
        flash('Only draft bills can be deleted.', 'warning')
        return redirect(url_for('purchases.index'))
    log_activity('delete', 'Bill', bill.id, bill.bill_number, f'Deleted bill {bill.bill_number}')
    db.session.delete(bill)
    db.session.commit()
    flash('Bill deleted.', 'success')
    return redirect(url_for('purchases.index'))


# ─── PAYMENTS MADE ────────────────────────────────────────
@purchases_bp.route('/payments')
@login_required
def payments():
    all_payments = PaymentMade.query.filter_by(user_id=current_user.id).order_by(PaymentMade.date.desc()).all()
    return render_template('purchases/payments.html', payments=all_payments)


@purchases_bp.route('/payments/create', methods=['GET', 'POST'])
@login_required
def create_payment():
    if request.method == 'POST':
        bill_id = request.form.get('bill_id') or None
        vendor_id = int(request.form['vendor_id'])
        amount = float(request.form['amount'])

        payment = PaymentMade(
            payment_number=get_next_payment_made_number(),
            vendor_id=vendor_id,
            bill_id=int(bill_id) if bill_id else None,
            date=date.fromisoformat(request.form['date']),
            amount=amount,
            payment_method=request.form.get('payment_method', 'cash'),
            reference=request.form.get('reference', ''),
            paid_from_account_id=int(request.form['paid_from_account_id']),
            notes=request.form.get('notes', ''),
            user_id=current_user.id,
        )

        # Create journal entry
        vendor = Vendor.query.filter_by(id=vendor_id, user_id=current_user.id).first()
        pje = create_payment_journal(payment, vendor.name if vendor else 'Vendor')
        if pje:
            payment.journal_entry_id = pje.id

        # Update bill — recalculate and set status
        if bill_id:
            bill = Bill.query.filter_by(id=int(bill_id), user_id=current_user.id).first()
            if bill:
                bill.amount_paid += amount
                bill.balance_due = bill.total - bill.amount_paid
                if bill.balance_due <= 0.01:
                    bill.status = 'paid'
                    bill.paid_date = payment.date
                    bill.balance_due = 0
                else:
                    bill.status = 'partial'

        # Update vendor balance
        if vendor:
            vendor.balance -= amount

        db.session.add(payment)
        db.session.commit()

        log_activity('create', 'Payment Made', payment.id, payment.payment_number,
                     f'Payment {payment.payment_number} of {amount:,.2f} to {vendor.name if vendor else "vendor"}')
        db.session.commit()

        if bill_id and bill and bill.status == 'paid':
            flash(f'Payment {payment.payment_number} recorded. Bill {bill.bill_number} is now FULLY PAID!', 'success')
        else:
            flash(f'Payment {payment.payment_number} recorded.', 'success')

        if bill_id:
            return redirect(url_for('purchases.view', id=int(bill_id)))
        return redirect(url_for('purchases.payments'))

    vendors = Vendor.query.filter_by(is_active=True, user_id=current_user.id).order_by(Vendor.name).all()
    bills = Bill.query.filter(Bill.status.in_(['owed', 'received', 'partial', 'overdue']), Bill.user_id == current_user.id).order_by(Bill.date.desc()).all()
    bank_accounts = Account.query.filter(Account.account_type == 'Asset',
                                          Account.sub_type.in_(['Current Asset']),
                                          Account.user_id == current_user.id).order_by(Account.code).all()

    # Pre-fill amount if bill_id is in query string
    prefill_bill = None
    if request.args.get('bill_id'):
        prefill_bill = Bill.query.filter_by(id=int(request.args.get('bill_id')), user_id=current_user.id).first()

    return render_template('purchases/payment_form.html', payment=None, vendors=vendors,
                           bills=bills, bank_accounts=bank_accounts, today=date.today(),
                           prefill_bill=prefill_bill)
