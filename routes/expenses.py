from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.models import db, Expense, Vendor, Account, JournalEntry, JournalLine, log_activity
from datetime import date

expenses_bp = Blueprint('expenses', __name__, url_prefix='/expenses')

# ── Petty-cash specific categories ──────────────────────────────
PETTY_CASH_CATEGORIES = [
    'Office Supplies',
    'Transportation & Parking',
    'Meals & Refreshments',
    'Postage & Courier',
    'Printing & Stationery',
    'Cleaning & Janitorial',
    'Repairs & Maintenance',
    'Utilities (minor)',
    'Miscellaneous',
]

# Map each petty-cash category to the most appropriate expense account code
_CATEGORY_ACCOUNT_MAP = {
    'Office Supplies':          '6300',   # Office Supplies
    'Transportation & Parking': '6700',   # Travel & Transportation
    'Meals & Refreshments':     '6950',   # Miscellaneous Expense
    'Postage & Courier':        '6300',   # Office Supplies
    'Printing & Stationery':    '6300',   # Office Supplies
    'Cleaning & Janitorial':    '6950',   # Miscellaneous Expense
    'Repairs & Maintenance':    '6950',   # Miscellaneous Expense
    'Utilities (minor)':        '6800',   # Utilities
    'Miscellaneous':            '6950',   # Miscellaneous Expense
}


def _get_petty_cash_account():
    """Return the Petty Cash (1050) account, fall back to Cash (1000)."""
    acct = Account.query.filter_by(code='1050', is_active=True, user_id=current_user.id).first()
    if acct is None:
        acct = Account.query.filter_by(code='1000', is_active=True, user_id=current_user.id).first()
    return acct


def _get_expense_account_for_category(category):
    """Return the matching expense account for a petty-cash category."""
    code = _CATEGORY_ACCOUNT_MAP.get(category, '6950')
    acct = Account.query.filter_by(code=code, is_active=True, user_id=current_user.id).first()
    if acct is None:
        acct = Account.query.filter_by(code='6950', is_active=True, user_id=current_user.id).first()
    return acct


def get_next_expense_number():
    last = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.id.desc()).first()
    num = (int(last.expense_number.replace('PC-', '').replace('EXP-', '')) + 1) if last else 1
    return f'PC-{num:05d}'


@expenses_bp.route('/')
@login_required
def index():
    all_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc(), Expense.id.desc()).all()
    # Compute running petty cash balance
    petty_cash_account = _get_petty_cash_account()
    pc_balance = 0.0
    if petty_cash_account:
        from sqlalchemy import func
        debits = db.session.query(func.coalesce(func.sum(JournalLine.debit), 0)).join(JournalEntry).filter(
            JournalLine.account_id == petty_cash_account.id,
            JournalEntry.user_id == current_user.id
        ).scalar()
        credits = db.session.query(func.coalesce(func.sum(JournalLine.credit), 0)).join(JournalEntry).filter(
            JournalLine.account_id == petty_cash_account.id,
            JournalEntry.user_id == current_user.id
        ).scalar()
        pc_balance = debits - credits
    return render_template('expenses/index.html', expenses=all_expenses,
                           pc_balance=pc_balance, petty_cash_account=petty_cash_account)


@expenses_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    petty_cash_acct = _get_petty_cash_account()

    if request.method == 'POST':
        amount = float(request.form['amount'])
        category = request.form.get('category', 'Miscellaneous')
        expense_account = _get_expense_account_for_category(category)

        expense = Expense(
            expense_number=get_next_expense_number(),
            user_id=current_user.id,
            date=date.fromisoformat(request.form['date']),
            category=category,
            vendor_id=None,
            expense_account_id=expense_account.id,
            paid_from_account_id=petty_cash_acct.id,
            amount=amount,
            payment_method='cash',
            reference=request.form.get('reference', ''),
            description=request.form.get('description', ''),
        )

        # Journal entry: Debit Expense account, Credit Petty Cash
        from routes.journal import get_next_entry_number
        je = JournalEntry(
            entry_number=get_next_entry_number(),
            user_id=current_user.id,
            date=expense.date,
            description=f'Petty Cash: {category}',
            reference=expense.expense_number,
            source='expense',
            is_posted=True,
        )
        je.lines.append(JournalLine(account_id=expense_account.id, debit=amount, credit=0, user_id=current_user.id))
        je.lines.append(JournalLine(account_id=petty_cash_acct.id, debit=0, credit=amount, user_id=current_user.id))
        db.session.add(je)
        db.session.flush()
        expense.journal_entry_id = je.id

        db.session.add(expense)
        db.session.commit()
        log_activity('create', 'Expense', expense.id, expense.expense_number,
                     f'Petty cash expense {expense.expense_number}: {category} {amount:,.2f}')
        db.session.commit()
        flash(f'Petty cash expense {expense.expense_number} recorded.', 'success')
        return redirect(url_for('expenses.index'))

    return render_template('expenses/form.html',
                           categories=PETTY_CASH_CATEGORIES,
                           petty_cash_acct=petty_cash_acct,
                           today=date.today())


@expenses_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    expense = Expense.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    log_activity('delete', 'Expense', expense.id, expense.expense_number,
                 f'Deleted expense {expense.expense_number}: {expense.amount:,.2f}')
    # Delete the linked journal entry (and its lines) first
    if expense.journal_entry:
        for line in list(expense.journal_entry.lines):
            db.session.delete(line)
        db.session.delete(expense.journal_entry)
    db.session.delete(expense)
    db.session.commit()
    flash('Petty cash expense deleted.', 'success')
    return redirect(url_for('expenses.index'))
