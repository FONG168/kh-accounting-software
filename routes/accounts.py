from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.models import db, Account, log_activity

accounts_bp = Blueprint('accounts', __name__, url_prefix='/accounts')


@accounts_bp.route('/')
@login_required
def index():
    accounts = Account.query.filter_by(user_id=current_user.id).order_by(Account.account_type, Account.code).all()
    # Group by type
    grouped = {}
    for acct in accounts:
        grouped.setdefault(acct.account_type, []).append(acct)
    return render_template('accounts/index.html', grouped=grouped, accounts=accounts)


@accounts_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        account = Account(
            code=request.form['code'],
            name=request.form['name'],
            account_type=request.form['account_type'],
            sub_type=request.form.get('sub_type', ''),
            description=request.form.get('description', ''),
            parent_id=request.form.get('parent_id') or None,
            normal_balance='credit' if request.form['account_type'] in ('Liability', 'Equity', 'Revenue') else 'debit',
            user_id=current_user.id
        )
        db.session.add(account)
        try:
            db.session.flush()
            log_activity('create', 'Account', account.id, f'{account.code} {account.name}',
                         f'Created account {account.code} - {account.name} ({account.account_type})')
            db.session.commit()
            flash('Account created successfully.', 'success')
            return redirect(url_for('accounts.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')

    parents = Account.query.filter_by(user_id=current_user.id).order_by(Account.code).all()
    return render_template('accounts/form.html', account=None, parents=parents)


@accounts_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    account = Account.query.get_or_404(id)
    if request.method == 'POST':
        account.code = request.form['code']
        account.name = request.form['name']
        account.account_type = request.form['account_type']
        account.sub_type = request.form.get('sub_type', '')
        account.description = request.form.get('description', '')
        account.parent_id = request.form.get('parent_id') or None
        account.normal_balance = 'credit' if request.form['account_type'] in ('Liability', 'Equity', 'Revenue') else 'debit'
        try:
            log_activity('update', 'Account', account.id, f'{account.code} {account.name}',
                         f'Updated account {account.code} - {account.name}')
            db.session.commit()
            flash('Account updated successfully.', 'success')
            return redirect(url_for('accounts.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')

    parents = Account.query.filter(Account.user_id == current_user.id).filter(Account.id != id).order_by(Account.code).all()
    return render_template('accounts/form.html', account=account, parents=parents)


@accounts_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    account = Account.query.get_or_404(id)
    if account.is_system:
        flash('System accounts cannot be deleted.', 'warning')
        return redirect(url_for('accounts.index'))
    if account.journal_lines.count() > 0:
        flash('Cannot delete account with journal entries.', 'warning')
        return redirect(url_for('accounts.index'))
    log_activity('delete', 'Account', account.id, f'{account.code} {account.name}',
                 f'Deleted account {account.code} - {account.name}')
    db.session.delete(account)
    db.session.commit()
    flash('Account deleted.', 'success')
    return redirect(url_for('accounts.index'))
