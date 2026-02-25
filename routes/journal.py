from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.models import db, JournalEntry, JournalLine, Account, FiscalPeriod, log_activity
from datetime import date

journal_bp = Blueprint('journal', __name__, url_prefix='/journal')


def get_next_entry_number():
    last = JournalEntry.query.filter_by(user_id=current_user.id).order_by(JournalEntry.id.desc()).first()
    if last:
        num = int(last.entry_number.replace('JE-', '')) + 1
    else:
        num = 1
    return f'JE-{num:05d}'


@journal_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 25
    pagination = JournalEntry.query.filter_by(user_id=current_user.id).order_by(
        JournalEntry.date.desc(), JournalEntry.id.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('journal/index.html', entries=pagination.items, pagination=pagination)


@journal_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        entry_date = date.fromisoformat(request.form['date'])

        # Period locking check
        if FiscalPeriod.is_period_locked(entry_date, current_user.id):
            flash(f'Cannot create journal entry in a locked fiscal period ({entry_date.strftime("%B %Y")}).', 'danger')
            accounts = Account.query.filter_by(is_active=True, user_id=current_user.id).order_by(Account.code).all()
            return render_template('journal/form.html', entry=None, accounts=accounts, today=date.today())

        entry = JournalEntry(
            entry_number=get_next_entry_number(),
            user_id=current_user.id,
            date=entry_date,
            description=request.form.get('description', ''),
            reference=request.form.get('reference', ''),
            source='manual',
            is_posted=('post' in request.form),
        )

        line_count = int(request.form.get('line_count', 0))
        for i in range(line_count):
            acct_id = request.form.get(f'lines-{i}-account_id')
            if not acct_id:
                continue
            debit = float(request.form.get(f'lines-{i}-debit', 0) or 0)
            credit = float(request.form.get(f'lines-{i}-credit', 0) or 0)
            if debit == 0 and credit == 0:
                continue
            line = JournalLine(
                account_id=int(acct_id),
                description=request.form.get(f'lines-{i}-description', ''),
                debit=debit,
                credit=credit,
                user_id=current_user.id,
            )
            entry.lines.append(line)

        if not entry.lines:
            flash('At least one journal line is required.', 'warning')
        elif not entry.is_balanced:
            flash('Journal entry must be balanced (debits = credits).', 'danger')
        else:
            db.session.add(entry)
            db.session.commit()
            log_activity('create', 'Journal Entry', entry.id, entry.entry_number,
                         f'Created journal entry {entry.entry_number}: {entry.description}')
            db.session.commit()
            flash(f'Journal entry {entry.entry_number} created.', 'success')
            return redirect(url_for('journal.index'))

    accounts = Account.query.filter_by(is_active=True, user_id=current_user.id).order_by(Account.code).all()
    return render_template('journal/form.html', entry=None, accounts=accounts, today=date.today())


@journal_bp.route('/view/<int:id>')
@login_required
def view(id):
    entry = JournalEntry.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return render_template('journal/view.html', entry=entry)


@journal_bp.route('/post/<int:id>', methods=['POST'])
@login_required
def post(id):
    entry = JournalEntry.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if not entry.is_balanced:
        flash('Cannot post an unbalanced entry.', 'danger')
    else:
        entry.is_posted = True
        log_activity('update', 'Journal Entry', entry.id, entry.entry_number,
                     f'Posted journal entry {entry.entry_number}')
        db.session.commit()
        flash(f'Journal entry {entry.entry_number} posted.', 'success')
    return redirect(url_for('journal.view', id=id))


@journal_bp.route('/reverse/<int:id>', methods=['POST'])
@login_required
def reverse(id):
    """Create a reversing entry for a posted journal entry."""
    original = JournalEntry.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if not original.is_posted:
        flash('Can only reverse posted entries.', 'warning')
        return redirect(url_for('journal.view', id=id))

    reversal_date = date.today()
    if FiscalPeriod.is_period_locked(reversal_date, current_user.id):
        flash(f'Cannot create reversal in a locked period ({reversal_date.strftime("%B %Y")}).', 'danger')
        return redirect(url_for('journal.view', id=id))

    reversal = JournalEntry(
        entry_number=get_next_entry_number(),
        user_id=current_user.id,
        date=reversal_date,
        description=f'Reversal of {original.entry_number}: {original.description}',
        reference=f'REV-{original.entry_number}',
        source='reversal',
        is_posted=True,
    )

    for line in original.lines:
        reversal.lines.append(JournalLine(
            account_id=line.account_id,
            description=f'Reversal: {line.description}',
            debit=line.credit,
            credit=line.debit,
            user_id=current_user.id,
        ))

    db.session.add(reversal)
    log_activity('create', 'Journal Entry', reversal.id, reversal.entry_number,
                 f'Created reversing entry {reversal.entry_number} for {original.entry_number}')
    db.session.commit()
    flash(f'Reversing entry {reversal.entry_number} created and posted.', 'success')
    return redirect(url_for('journal.view', id=reversal.id))


@journal_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    entry = JournalEntry.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if entry.is_posted:
        flash('Cannot delete a posted entry. Create a reversing entry instead.', 'warning')
        return redirect(url_for('journal.index'))
    log_activity('delete', 'Journal Entry', entry.id, entry.entry_number,
                 f'Deleted journal entry {entry.entry_number}')
    db.session.delete(entry)
    db.session.commit()
    flash('Journal entry deleted.', 'success')
    return redirect(url_for('journal.index'))
