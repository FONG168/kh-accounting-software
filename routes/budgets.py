from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.models import db, Budget, Account, log_activity
from datetime import date
import calendar

budgets_bp = Blueprint('budgets', __name__, url_prefix='/budgets')


@budgets_bp.route('/')
@login_required
def index():
    """List all budgets, grouped by year."""
    year = request.args.get('year', date.today().year, type=int)
    budgets = Budget.query.filter_by(user_id=current_user.id, year=year).order_by(
        Budget.account_id, Budget.month
    ).all()

    # Build summary by account
    account_budgets = {}
    for b in budgets:
        if b.account_id not in account_budgets:
            account_budgets[b.account_id] = {
                'account': b.account,
                'months': {},
                'total': 0,
            }
        account_budgets[b.account_id]['months'][b.month] = float(b.amount)
        account_budgets[b.account_id]['total'] += float(b.amount)

    current_year = date.today().year
    years = list(range(current_year - 2, current_year + 3))
    return render_template('budgets/index.html', account_budgets=account_budgets,
                           year=year, years=years, months=list(range(1, 13)),
                           month_names=calendar.month_abbr)


@budgets_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create or edit budget entries for a specific account and year."""
    if request.method == 'POST':
        account_id = int(request.form['account_id'])
        year = int(request.form['year'])

        for month in range(1, 13):
            amount = float(request.form.get(f'month_{month}', 0) or 0)
            existing = Budget.query.filter_by(
                user_id=current_user.id, account_id=account_id, year=year, month=month
            ).first()
            if existing:
                existing.amount = amount
            else:
                if amount > 0:
                    db.session.add(Budget(
                        account_id=account_id,
                        year=year,
                        month=month,
                        amount=amount,
                        notes=request.form.get('notes', ''),
                        user_id=current_user.id,
                    ))

        db.session.commit()
        account = Account.query.filter_by(id=account_id, user_id=current_user.id).first()
        log_activity('create', 'Budget', account_id, f'{account.name} {year}',
                     f'Set budget for {account.name} - {year}')
        db.session.commit()
        flash(f'Budget for {account.name} ({year}) saved.', 'success')
        return redirect(url_for('budgets.index', year=year))

    accounts = Account.query.filter(
        Account.user_id == current_user.id,
        Account.account_type.in_(['Revenue', 'Expense'])
    ).order_by(Account.code).all()
    year = request.args.get('year', date.today().year, type=int)
    account_id = request.args.get('account_id', type=int)

    # Pre-fill with existing data if editing
    existing_data = {}
    if account_id:
        existing = Budget.query.filter_by(user_id=current_user.id, account_id=account_id, year=year).all()
        for b in existing:
            existing_data[b.month] = float(b.amount)

    current_year = date.today().year
    years = list(range(current_year - 2, current_year + 3))
    return render_template('budgets/form.html', accounts=accounts, year=year,
                           years=years, account_id=account_id,
                           existing_data=existing_data,
                           month_names=calendar.month_name)


@budgets_bp.route('/delete/<int:account_id>/<int:year>', methods=['POST'])
@login_required
def delete(account_id, year):
    """Delete all budget entries for an account/year."""
    Budget.query.filter_by(user_id=current_user.id, account_id=account_id, year=year).delete()
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first()
    log_activity('delete', 'Budget', account_id, f'{account.name} {year}',
                 f'Deleted budget for {account.name} - {year}')
    db.session.commit()
    flash(f'Budget for {account.name} ({year}) deleted.', 'success')
    return redirect(url_for('budgets.index', year=year))
