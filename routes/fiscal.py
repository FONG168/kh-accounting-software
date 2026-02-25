from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.models import db, FiscalPeriod, log_activity
from datetime import datetime, date
import calendar

fiscal_bp = Blueprint('fiscal', __name__, url_prefix='/fiscal')


@fiscal_bp.route('/')
@login_required
def index():
    """Show all fiscal periods with lock status."""
    # Generate periods for the current and previous year if they don't exist
    current_year = date.today().year
    for year in [current_year - 1, current_year, current_year + 1]:
        for month in range(1, 13):
            existing = FiscalPeriod.query.filter_by(year=year, month=month, user_id=current_user.id).first()
            if not existing:
                db.session.add(FiscalPeriod(year=year, month=month, is_locked=False, user_id=current_user.id))
    db.session.commit()

    periods = FiscalPeriod.query.filter_by(user_id=current_user.id).order_by(
        FiscalPeriod.year.desc(), FiscalPeriod.month.desc()
    ).all()

    # Enrich with month names
    for p in periods:
        p.month_name = calendar.month_name[p.month]

    return render_template('fiscal/index.html', periods=periods)


@fiscal_bp.route('/lock/<int:id>', methods=['POST'])
@login_required
def lock(id):
    """Lock a fiscal period to prevent transaction modifications."""
    period = FiscalPeriod.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    if period.is_locked:
        flash(f'{calendar.month_name[period.month]} {period.year} is already locked.', 'info')
        return redirect(url_for('fiscal.index'))

    period.is_locked = True
    period.locked_by_id = current_user.id
    period.locked_at = datetime.utcnow()
    period.notes = request.form.get('notes', '')

    log_activity('update', 'Fiscal Period', period.id, f'{period.year}-{period.month:02d}',
                 f'Locked fiscal period {calendar.month_name[period.month]} {period.year}')
    db.session.commit()
    flash(f'{calendar.month_name[period.month]} {period.year} has been locked.', 'success')
    return redirect(url_for('fiscal.index'))


@fiscal_bp.route('/unlock/<int:id>', methods=['POST'])
@login_required
def unlock(id):
    """Unlock a fiscal period (admin only)."""
    period = FiscalPeriod.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    if not period.is_locked:
        flash(f'{calendar.month_name[period.month]} {period.year} is already open.', 'info')
        return redirect(url_for('fiscal.index'))

    period.is_locked = False
    period.locked_by_id = None
    period.locked_at = None

    log_activity('update', 'Fiscal Period', period.id, f'{period.year}-{period.month:02d}',
                 f'Unlocked fiscal period {calendar.month_name[period.month]} {period.year}')
    db.session.commit()
    flash(f'{calendar.month_name[period.month]} {period.year} has been unlocked.', 'success')
    return redirect(url_for('fiscal.index'))


@fiscal_bp.route('/year-end', methods=['GET', 'POST'])
@login_required
def year_end():
    """Year-end closing process: close revenue/expense accounts to Retained Earnings."""
    if request.method == 'POST':
        fiscal_year = int(request.form['fiscal_year'])

        from database.models import Account, JournalEntry, JournalLine
        from routes.journal import get_next_entry_number
        from sqlalchemy import func

        # Get Retained Earnings account
        re_account = Account.query.filter_by(code='3200', user_id=current_user.id).first()
        if not re_account:
            flash('Retained Earnings account (3200) not found. Please create it first.', 'danger')
            return redirect(url_for('fiscal.year_end'))

        # Sum all revenue and expense journal lines for the fiscal year
        from flask import current_app
        start_month = current_app.config.get('FISCAL_YEAR_START_MONTH', 1)
        if start_month == 1:
            fy_start = date(fiscal_year, 1, 1)
            fy_end = date(fiscal_year, 12, 31)
        else:
            fy_start = date(fiscal_year, start_month, 1)
            fy_end = date(fiscal_year + 1, start_month - 1,
                          calendar.monthrange(fiscal_year + 1, start_month - 1)[1])

        # Get all revenue accounts (type 'Revenue') and expense accounts (type 'Expense')
        revenue_accounts = Account.query.filter_by(account_type='Revenue', user_id=current_user.id).all()
        expense_accounts = Account.query.filter_by(account_type='Expense', user_id=current_user.id).all()

        closing_entry = JournalEntry(
            entry_number=get_next_entry_number(),
            user_id=current_user.id,
            date=fy_end,
            description=f'Year-end closing entry for fiscal year {fiscal_year}',
            reference=f'YE-{fiscal_year}',
            source='year_end',
            is_posted=True,
        )

        net_income = 0

        # Close revenue accounts (normally credit balance → debit to close)
        for acct in revenue_accounts:
            balance = db.session.query(
                func.coalesce(func.sum(JournalLine.credit), 0) -
                func.coalesce(func.sum(JournalLine.debit), 0)
            ).join(JournalEntry).filter(
                JournalLine.account_id == acct.id,
                JournalEntry.date >= fy_start,
                JournalEntry.date <= fy_end,
                JournalEntry.is_posted == True,
                JournalEntry.user_id == current_user.id,
            ).scalar() or 0

            balance = float(balance)
            if abs(balance) > 0.01:
                closing_entry.lines.append(JournalLine(
                    account_id=acct.id,
                    debit=balance if balance > 0 else 0,
                    credit=abs(balance) if balance < 0 else 0,
                    description=f'Close {acct.name}',
                    user_id=current_user.id,
                ))
                net_income += balance

        # Close expense accounts (normally debit balance → credit to close)
        for acct in expense_accounts:
            balance = db.session.query(
                func.coalesce(func.sum(JournalLine.debit), 0) -
                func.coalesce(func.sum(JournalLine.credit), 0)
            ).join(JournalEntry).filter(
                JournalLine.account_id == acct.id,
                JournalEntry.date >= fy_start,
                JournalEntry.date <= fy_end,
                JournalEntry.is_posted == True,
                JournalEntry.user_id == current_user.id,
            ).scalar() or 0

            balance = float(balance)
            if abs(balance) > 0.01:
                closing_entry.lines.append(JournalLine(
                    account_id=acct.id,
                    debit=0 if balance > 0 else abs(balance),
                    credit=balance if balance > 0 else 0,
                    description=f'Close {acct.name}',
                    user_id=current_user.id,
                ))
                net_income -= balance

        # Transfer net income to Retained Earnings
        if abs(net_income) > 0.01:
            closing_entry.lines.append(JournalLine(
                account_id=re_account.id,
                debit=0 if net_income > 0 else abs(net_income),
                credit=net_income if net_income > 0 else 0,
                description=f'Net income to Retained Earnings',
                user_id=current_user.id,
            ))

        if closing_entry.lines:
            db.session.add(closing_entry)
            log_activity('create', 'Journal Entry', closing_entry.id, closing_entry.entry_number,
                         f'Year-end closing for FY {fiscal_year}, net income: {net_income:,.2f}')
            db.session.commit()
            flash(f'Year-end closing entry created. Net income: {net_income:,.2f}', 'success')
        else:
            flash('No balances to close for the selected fiscal year.', 'info')

        return redirect(url_for('fiscal.index'))

    current_year = date.today().year
    years = list(range(current_year - 5, current_year + 1))
    return render_template('fiscal/year_end.html', years=years, current_year=current_year)
