from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, current_app
from database.models import (db, Account, JournalEntry, JournalLine, Invoice, Bill,
                             Product, Expense, Customer, Vendor, Budget,
                             PaymentReceived, PaymentMade)
from datetime import date, timedelta
from sqlalchemy import func
import calendar

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


def get_date_range():
    """Get date range from query parameters or default to current year."""
    today = date.today()
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    if start:
        start = date.fromisoformat(start)
    else:
        start = date(today.year, 1, 1)
    if end:
        end = date.fromisoformat(end)
    else:
        end = today
    return start, end


def get_account_balance(account_id, start_date=None, end_date=None):
    """Calculate account balance for a period."""
    query = db.session.query(
        func.coalesce(func.sum(JournalLine.debit), 0).label('total_debit'),
        func.coalesce(func.sum(JournalLine.credit), 0).label('total_credit')
    ).join(JournalEntry).filter(
        JournalLine.account_id == account_id,
        JournalEntry.is_posted == True,
        JournalEntry.user_id == current_user.id
    )
    if start_date:
        query = query.filter(JournalEntry.date >= start_date)
    if end_date:
        query = query.filter(JournalEntry.date <= end_date)
    result = query.first()
    return result.total_debit or 0, result.total_credit or 0


# ─── PROFIT & LOSS (INCOME STATEMENT) ────────────────────
@reports_bp.route('/profit-loss')
@login_required
def profit_loss():
    start, end = get_date_range()

    # Comparative prior period (same length, one year back)
    period_days = (end - start).days
    prior_end = start - timedelta(days=1)
    prior_start = prior_end - timedelta(days=period_days)

    revenue_accounts = Account.query.filter_by(account_type='Revenue', is_active=True, user_id=current_user.id).order_by(Account.code).all()
    expense_accounts = Account.query.filter_by(account_type='Expense', is_active=True, user_id=current_user.id).order_by(Account.code).all()

    revenue_data = []
    total_revenue = 0
    prior_total_revenue = 0
    for acct in revenue_accounts:
        debit, credit = get_account_balance(acct.id, start, end)
        balance = credit - debit
        pd, pc = get_account_balance(acct.id, prior_start, prior_end)
        prior_balance = pc - pd
        if abs(balance) > 0.001 or abs(prior_balance) > 0.001:
            revenue_data.append({'account': acct, 'balance': balance, 'prior': prior_balance})
            total_revenue += balance
            prior_total_revenue += prior_balance

    # ── Separate COGS (Cost of Sales) from Operating Expenses ──
    cogs_data = []
    total_cogs = 0
    prior_total_cogs = 0
    expense_data = []
    total_expenses = 0
    prior_total_expenses = 0
    for acct in expense_accounts:
        debit, credit = get_account_balance(acct.id, start, end)
        balance = debit - credit
        pd, pc = get_account_balance(acct.id, prior_start, prior_end)
        prior_balance = pd - pc
        if abs(balance) > 0.001 or abs(prior_balance) > 0.001:
            entry = {'account': acct, 'balance': balance, 'prior': prior_balance}
            if acct.sub_type == 'Cost of Sales':
                cogs_data.append(entry)
                total_cogs += balance
                prior_total_cogs += prior_balance
            else:
                expense_data.append(entry)
                total_expenses += balance
                prior_total_expenses += prior_balance

    gross_profit = total_revenue - total_cogs
    prior_gross_profit = prior_total_revenue - prior_total_cogs
    all_total_expenses = total_cogs + total_expenses
    prior_all_total_expenses = prior_total_cogs + prior_total_expenses
    net_income = total_revenue - all_total_expenses
    prior_net_income = prior_total_revenue - prior_all_total_expenses

    return render_template('reports/profit_loss.html',
                           revenue_data=revenue_data,
                           cogs_data=cogs_data, total_cogs=total_cogs,
                           prior_total_cogs=prior_total_cogs,
                           gross_profit=gross_profit, prior_gross_profit=prior_gross_profit,
                           expense_data=expense_data,
                           total_revenue=total_revenue, total_expenses=total_expenses,
                           net_income=net_income,
                           prior_total_revenue=prior_total_revenue,
                           prior_total_expenses=prior_total_expenses,
                           prior_net_income=prior_net_income,
                           start=start, end=end,
                           prior_start=prior_start, prior_end=prior_end)


# ─── BALANCE SHEET ────────────────────────────────────────
@reports_bp.route('/balance-sheet')
@login_required
def balance_sheet():
    end = request.args.get('end_date')
    if end:
        end = date.fromisoformat(end)
    else:
        end = date.today()

    # Comparative: same date one year prior
    prior_end = date(end.year - 1, end.month, min(end.day, 28))

    asset_accounts = Account.query.filter_by(account_type='Asset', is_active=True, user_id=current_user.id).order_by(Account.code).all()
    liability_accounts = Account.query.filter_by(account_type='Liability', is_active=True, user_id=current_user.id).order_by(Account.code).all()
    equity_accounts = Account.query.filter_by(account_type='Equity', is_active=True, user_id=current_user.id).order_by(Account.code).all()

    def build_section(accounts, normal='debit', as_of=None):
        data = []
        total = 0
        for acct in accounts:
            debit, credit = get_account_balance(acct.id, None, as_of)
            if normal == 'debit':
                balance = debit - credit
            else:
                balance = credit - debit
            if abs(balance) > 0.001:
                data.append({'account': acct, 'balance': balance})
                total += balance
        return data, total

    asset_data, total_assets = build_section(asset_accounts, 'debit', end)
    liability_data, total_liabilities = build_section(liability_accounts, 'credit', end)
    equity_data, total_equity = build_section(equity_accounts, 'credit', end)

    # Prior period
    _, prior_total_assets = build_section(asset_accounts, 'debit', prior_end)
    _, prior_total_liabilities = build_section(liability_accounts, 'credit', prior_end)
    _, prior_total_equity = build_section(equity_accounts, 'credit', prior_end)

    # Calculate retained earnings (net income this fiscal year)
    fy_start_month = current_app.config.get('FISCAL_YEAR_START_MONTH', 1)
    if fy_start_month == 1:
        year_start = date(end.year, 1, 1)
    else:
        year_start = date(end.year if end.month >= fy_start_month else end.year - 1, fy_start_month, 1)
    revenue_accounts = Account.query.filter_by(account_type='Revenue', user_id=current_user.id).all()
    expense_accts = Account.query.filter_by(account_type='Expense', user_id=current_user.id).all()
    net_income = 0
    for acct in revenue_accounts:
        d, c = get_account_balance(acct.id, year_start, end)
        net_income += (c - d)
    for acct in expense_accts:
        d, c = get_account_balance(acct.id, year_start, end)
        net_income -= (d - c)

    total_equity += net_income

    return render_template('reports/balance_sheet.html',
                           asset_data=asset_data, liability_data=liability_data,
                           equity_data=equity_data,
                           total_assets=total_assets,
                           total_liabilities=total_liabilities,
                           total_equity=total_equity,
                           net_income=net_income,
                           prior_total_assets=prior_total_assets,
                           prior_total_liabilities=prior_total_liabilities,
                           prior_total_equity=prior_total_equity,
                           prior_end=prior_end,
                           end=end)


# ─── TRIAL BALANCE ────────────────────────────────────────
@reports_bp.route('/trial-balance')
@login_required
def trial_balance():
    start, end = get_date_range()
    accounts = Account.query.filter_by(is_active=True, user_id=current_user.id).order_by(Account.account_type, Account.code).all()

    data = []
    total_debit = 0
    total_credit = 0
    for acct in accounts:
        debit, credit = get_account_balance(acct.id, start, end)
        net_debit = max(debit - credit, 0)
        net_credit = max(credit - debit, 0)
        if abs(debit) > 0.001 or abs(credit) > 0.001:
            data.append({
                'account': acct,
                'debit': net_debit,
                'credit': net_credit,
            })
            total_debit += net_debit
            total_credit += net_credit

    return render_template('reports/trial_balance.html',
                           data=data, total_debit=total_debit, total_credit=total_credit,
                           start=start, end=end)


# ─── CASH FLOW STATEMENT (Indirect Method) ───────────────
@reports_bp.route('/cash-flow')
@login_required
def cash_flow():
    """
    Indirect-method Cash Flow Statement (IAS 7 / ASC 230).

    Section 1 – Operating:
        Start with Net Income, adjust for non-cash items (depreciation),
        then adjust for working-capital changes (AR, AP, Inventory, Prepaid).
    Section 2 – Investing:
        Track actual cash movements where the counter-account is a Fixed Asset.
    Section 3 – Financing:
        Track actual cash movements where the counter-account is Equity
        or a Long-term Liability.
    Closing Cash = Opening Cash + Operating + Investing + Financing
    """
    from collections import defaultdict

    start, end = get_date_range()

    # ────────────────────────────────────────────────────────
    # A.  Cash / Bank accounts & Opening Balance
    # ────────────────────────────────────────────────────────
    cash_accounts = Account.query.filter(
        Account.account_type == 'Asset',
        Account.code.in_(['1000', '1050', '1100']),          # Cash, Petty Cash, Bank
        Account.user_id == current_user.id
    ).all()
    cash_ids = {a.id for a in cash_accounts}

    opening_cash = 0.0
    for aid in cash_ids:
        d, c = get_account_balance(aid, None, start - timedelta(days=1))
        opening_cash += (d - c)

    # ────────────────────────────────────────────────────────
    # B.  Net Income for the period  (Revenue − Expenses)
    # ────────────────────────────────────────────────────────
    revenue_accts = Account.query.filter_by(account_type='Revenue', user_id=current_user.id).all()
    expense_accts = Account.query.filter_by(account_type='Expense', user_id=current_user.id).all()

    total_revenue = 0.0
    for acct in revenue_accts:
        d, c = get_account_balance(acct.id, start, end)
        total_revenue += (c - d)

    total_expenses = 0.0
    for acct in expense_accts:
        d, c = get_account_balance(acct.id, start, end)
        total_expenses += (d - c)

    net_income = total_revenue - total_expenses

    # ────────────────────────────────────────────────────────
    # C.  Non-cash adjustments  (add back Depreciation)
    # ────────────────────────────────────────────────────────
    depreciation_acct = Account.query.filter_by(code='6900', is_active=True, user_id=current_user.id).first()
    depreciation = 0.0
    if depreciation_acct:
        d, c = get_account_balance(depreciation_acct.id, start, end)
        depreciation = d - c          # positive = expense recorded

    # ────────────────────────────────────────────────────────
    # D.  Working-capital changes
    #     Compare ending balance vs beginning balance.
    #     For assets  (AR, Inventory, Prepaid): increase = cash outflow (negative)
    #     For liabilities (AP, Accrued):         increase = cash inflow (positive)
    # ────────────────────────────────────────────────────────
    wc_items = []

    def _wc_change(code, label, normal='debit'):
        """Return (label, amount) where +amount = cash inflow."""
        acct = Account.query.filter_by(code=code, is_active=True, user_id=current_user.id).first()
        if not acct:
            return None
        d0, c0 = get_account_balance(acct.id, None, start - timedelta(days=1))
        d1, c1 = get_account_balance(acct.id, None, end)
        if normal == 'debit':
            bal_start = d0 - c0
            bal_end   = d1 - c1
            change    = bal_end - bal_start
            cash_effect = -change   # asset increase → cash outflow
        else:
            bal_start = c0 - d0
            bal_end   = c1 - d1
            change    = bal_end - bal_start
            cash_effect = change    # liability increase → cash inflow
        if abs(cash_effect) > 0.001:
            return {'label': label, 'amount': cash_effect}
        return None

    # Current-asset working-capital accounts
    for code, label in [
        ('1200', 'Accounts Receivable'),
        ('1300', 'Inventory'),
        ('1400', 'Prepaid Expenses'),
    ]:
        item = _wc_change(code, label, 'debit')
        if item:
            wc_items.append(item)

    # Current-liability working-capital accounts
    for code, label in [
        ('2000', 'Accounts Payable'),
        ('2100', 'Accrued Expenses'),
        ('2200', 'Sales Tax Payable'),
    ]:
        item = _wc_change(code, label, 'credit')
        if item:
            wc_items.append(item)

    total_wc_changes = sum(i['amount'] for i in wc_items)

    operating_cash = net_income + depreciation + total_wc_changes

    # ────────────────────────────────────────────────────────
    # E.  Investing & Financing Activities
    #     Trace actual cash/bank movements and classify by counter-account.
    # ────────────────────────────────────────────────────────
    je_ids_q = (
        db.session.query(JournalLine.journal_entry_id)
        .join(JournalEntry)
        .filter(
            JournalLine.account_id.in_(cash_ids),
            JournalEntry.date >= start,
            JournalEntry.date <= end,
            JournalEntry.is_posted == True,
            JournalEntry.user_id == current_user.id,
        )
        .distinct()
    )
    je_id_list = [row[0] for row in je_ids_q.all()]

    all_lines = (
        JournalLine.query
        .filter(JournalLine.journal_entry_id.in_(je_id_list),
                JournalLine.user_id == current_user.id)
        .all()
    ) if je_id_list else []

    je_groups = defaultdict(list)
    for line in all_lines:
        je_groups[line.journal_entry_id].append(line)

    all_acct_ids = {l.account_id for l in all_lines}
    acct_map = {a.id: a for a in Account.query.filter(Account.id.in_(all_acct_ids), Account.user_id == current_user.id).all()} if all_acct_ids else {}

    investing_items = []
    financing_items = []

    for je_id, lines in je_groups.items():
        net_cash = sum(
            (l.debit or 0) - (l.credit or 0)
            for l in lines if l.account_id in cash_ids
        )
        if abs(net_cash) < 0.001:
            continue

        other_accts = [
            acct_map[l.account_id]
            for l in lines
            if l.account_id not in cash_ids and l.account_id in acct_map
        ]

        je = JournalEntry.query.filter_by(id=je_id, user_id=current_user.id).first()
        desc = je.description if je else ''

        for acct in other_accts:
            if acct.sub_type == 'Fixed Asset':
                label = 'Sale of assets' if net_cash > 0 else 'Purchase of assets'
                investing_items.append({'label': f'{label} ({acct.name})', 'amount': net_cash})
                net_cash = 0
                break
            if acct.account_type == 'Equity':
                label = 'Capital contributed' if net_cash > 0 else "Owner's draw"
                financing_items.append({'label': label, 'amount': net_cash})
                net_cash = 0
                break
            if acct.sub_type == 'Long-term Liability':
                label = 'Loan proceeds' if net_cash > 0 else 'Loan repayment'
                financing_items.append({'label': label, 'amount': net_cash})
                net_cash = 0
                break
            if acct.sub_type == 'Current Liability' and acct.code == '2300':
                label = 'Short-term borrowing' if net_cash > 0 else 'Short-term loan repayment'
                financing_items.append({'label': label, 'amount': net_cash})
                net_cash = 0
                break

    investing_cash = sum(i['amount'] for i in investing_items)
    financing_cash = sum(i['amount'] for i in financing_items)

    # ────────────────────────────────────────────────────────
    # F.  Net Change & Closing
    # ────────────────────────────────────────────────────────
    net_change = operating_cash + investing_cash + financing_cash
    closing_cash = opening_cash + net_change

    return render_template('reports/cash_flow.html',
                           opening_cash=opening_cash,
                           # Operating
                           net_income=net_income,
                           depreciation=depreciation,
                           wc_items=wc_items,
                           total_wc_changes=total_wc_changes,
                           operating_cash=operating_cash,
                           # Investing
                           investing_items=investing_items,
                           investing_cash=investing_cash,
                           # Financing
                           financing_items=financing_items,
                           financing_cash=financing_cash,
                           # Totals
                           net_change=net_change,
                           closing_cash=closing_cash,
                           start=start, end=end)


# ─── SALES REPORT ─────────────────────────────────────────
@reports_bp.route('/sales-report')
@login_required
def sales_report():
    start, end = get_date_range()
    invoices = Invoice.query.filter(
        Invoice.date >= start, Invoice.date <= end,
        Invoice.status != 'draft',
        Invoice.user_id == current_user.id
    ).order_by(Invoice.date.desc()).all()

    total_sales = sum(inv.total for inv in invoices)
    total_paid = sum(inv.amount_paid for inv in invoices)
    total_outstanding = sum(inv.balance_due for inv in invoices)

    # Daily sales summary
    daily = db.session.query(
        Invoice.date,
        func.sum(Invoice.total).label('total'),
        func.count(Invoice.id).label('count')
    ).filter(
        Invoice.date >= start, Invoice.date <= end,
        Invoice.status != 'draft',
        Invoice.user_id == current_user.id
    ).group_by(Invoice.date).order_by(Invoice.date.desc()).all()

    return render_template('reports/sales_report.html',
                           invoices=invoices, daily=daily,
                           total_sales=total_sales, total_paid=total_paid,
                           total_outstanding=total_outstanding,
                           start=start, end=end)


# ─── EXPENSE REPORT ───────────────────────────────────────
@reports_bp.route('/expense-report')
@login_required
def expense_report():
    start, end = get_date_range()
    expenses = Expense.query.filter(
        Expense.date >= start, Expense.date <= end,
        Expense.user_id == current_user.id
    ).order_by(Expense.date.desc()).all()

    total_expenses = sum(e.amount for e in expenses)

    # By category
    by_category = db.session.query(
        Expense.category,
        func.sum(Expense.amount).label('total'),
        func.count(Expense.id).label('count')
    ).filter(
        Expense.date >= start, Expense.date <= end,
        Expense.user_id == current_user.id
    ).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all()

    return render_template('reports/expense_report.html',
                           expenses=expenses, by_category=by_category,
                           total_expenses=total_expenses,
                           start=start, end=end)


# ─── INVENTORY REPORT ─────────────────────────────────────
@reports_bp.route('/inventory-report')
@login_required
def inventory_report():
    products = Product.query.filter_by(is_active=True, is_service=False, user_id=current_user.id).order_by(Product.category, Product.name).all()

    total_value = sum(p.quantity_on_hand * p.cost_price for p in products)
    low_stock = [p for p in products if p.quantity_on_hand <= p.reorder_level and p.reorder_level > 0]
    out_of_stock = [p for p in products if p.quantity_on_hand <= 0]

    return render_template('reports/inventory_report.html',
                           products=products, total_value=total_value,
                           low_stock=low_stock, out_of_stock=out_of_stock)


# ─── ACCOUNTS RECEIVABLE AGING ────────────────────────────
@reports_bp.route('/ar-aging')
@login_required
def ar_aging():
    today = date.today()
    invoices = Invoice.query.filter(
        Invoice.status.in_(['sent', 'owed', 'partial', 'overdue']),
        Invoice.balance_due > 0,
        Invoice.user_id == current_user.id
    ).order_by(Invoice.customer_id, Invoice.date).all()

    aging_data = []
    for inv in invoices:
        days = (today - inv.date).days
        if days <= 30:
            bucket = 'current'
        elif days <= 60:
            bucket = '31-60'
        elif days <= 90:
            bucket = '61-90'
        else:
            bucket = '90+'
        aging_data.append({
            'invoice': inv,
            'days': days,
            'bucket': bucket,
        })

    # Summary by customer
    customer_aging = {}
    for item in aging_data:
        cid = item['invoice'].customer_id
        if cid not in customer_aging:
            customer_aging[cid] = {
                'customer': item['invoice'].customer,
                'current': 0, '31-60': 0, '61-90': 0, '90+': 0, 'total': 0
            }
        customer_aging[cid][item['bucket']] += item['invoice'].balance_due
        customer_aging[cid]['total'] += item['invoice'].balance_due

    return render_template('reports/ar_aging.html',
                           aging_data=aging_data,
                           customer_aging=list(customer_aging.values()),
                           today=today)


# ─── ACCOUNTS PAYABLE AGING ──────────────────────────────
@reports_bp.route('/ap-aging')
@login_required
def ap_aging():
    today = date.today()
    bills = Bill.query.filter(
        Bill.status.in_(['received', 'owed', 'partial', 'overdue']),
        Bill.balance_due > 0,
        Bill.user_id == current_user.id
    ).order_by(Bill.vendor_id, Bill.date).all()

    aging_data = []
    for bill in bills:
        days = (today - bill.date).days
        if days <= 30:
            bucket = 'current'
        elif days <= 60:
            bucket = '31-60'
        elif days <= 90:
            bucket = '61-90'
        else:
            bucket = '90+'
        aging_data.append({
            'bill': bill,
            'days': days,
            'bucket': bucket,
        })

    vendor_aging = {}
    for item in aging_data:
        vid = item['bill'].vendor_id
        if vid not in vendor_aging:
            vendor_aging[vid] = {
                'vendor': item['bill'].vendor,
                'current': 0, '31-60': 0, '61-90': 0, '90+': 0, 'total': 0
            }
        vendor_aging[vid][item['bucket']] += item['bill'].balance_due
        vendor_aging[vid]['total'] += item['bill'].balance_due

    return render_template('reports/ap_aging.html',
                           aging_data=aging_data,
                           vendor_aging=list(vendor_aging.values()),
                           today=today)


# ─── GENERAL LEDGER ───────────────────────────────────────
@reports_bp.route('/general-ledger')
@login_required
def general_ledger():
    """General Ledger: shows all transactions per account with running balance."""
    start, end = get_date_range()
    account_id = request.args.get('account_id', type=int)

    accounts = Account.query.filter_by(is_active=True, user_id=current_user.id).order_by(Account.code).all()

    ledger_data = None
    selected_account = None
    if account_id:
        selected_account = Account.query.filter_by(id=account_id, user_id=current_user.id).first()
        if selected_account:
            # Get opening balance (before start date)
            d0, c0 = get_account_balance(account_id, None, start - timedelta(days=1))
            if selected_account.account_type in ('Asset', 'Expense'):
                opening_balance = d0 - c0
            else:
                opening_balance = c0 - d0

            # Get all journal lines in the period
            lines = (
                db.session.query(JournalLine, JournalEntry)
                .join(JournalEntry)
                .filter(
                    JournalLine.account_id == account_id,
                    JournalEntry.date >= start,
                    JournalEntry.date <= end,
                    JournalEntry.is_posted == True,
                    JournalEntry.user_id == current_user.id,
                )
                .order_by(JournalEntry.date, JournalEntry.id)
                .all()
            )

            running_balance = opening_balance
            entries = []
            for line, je in lines:
                debit = float(line.debit or 0)
                credit = float(line.credit or 0)
                if selected_account.account_type in ('Asset', 'Expense'):
                    running_balance += debit - credit
                else:
                    running_balance += credit - debit
                entries.append({
                    'date': je.date,
                    'entry_number': je.entry_number,
                    'description': je.description or line.description,
                    'reference': je.reference,
                    'debit': debit,
                    'credit': credit,
                    'balance': running_balance,
                })

            ledger_data = {
                'opening_balance': opening_balance,
                'entries': entries,
                'closing_balance': running_balance,
            }

    return render_template('reports/general_ledger.html',
                           accounts=accounts, selected_account=selected_account,
                           ledger_data=ledger_data, account_id=account_id,
                           start=start, end=end)


# ─── STATEMENT OF CHANGES IN EQUITY (IAS 1.106) ──────────
@reports_bp.route('/equity-statement')
@login_required
def equity_statement():
    """Statement of Changes in Equity per IAS 1.106."""
    start, end = get_date_range()

    equity_accounts = Account.query.filter_by(
        account_type='Equity', is_active=True, user_id=current_user.id
    ).order_by(Account.code).all()

    rows = []
    total_opening = 0
    total_closing = 0
    total_changes = 0

    for acct in equity_accounts:
        # Opening balance (before start date)
        d0, c0 = get_account_balance(acct.id, None, start - timedelta(days=1))
        opening = c0 - d0  # Equity normal = credit

        # Changes during period
        d_period, c_period = get_account_balance(acct.id, start, end)
        change = c_period - d_period

        closing = opening + change

        rows.append({
            'account': acct,
            'opening': opening,
            'change': change,
            'closing': closing,
        })
        total_opening += opening
        total_changes += change
        total_closing += closing

    # Net income for the period (to show as a separate line)
    revenue_accts = Account.query.filter_by(account_type='Revenue', user_id=current_user.id).all()
    expense_accts = Account.query.filter_by(account_type='Expense', user_id=current_user.id).all()
    net_income = 0
    for acct in revenue_accts:
        d, c = get_account_balance(acct.id, start, end)
        net_income += (c - d)
    for acct in expense_accts:
        d, c = get_account_balance(acct.id, start, end)
        net_income -= (d - c)

    return render_template('reports/equity_statement.html',
                           rows=rows, net_income=net_income,
                           total_opening=total_opening,
                           total_changes=total_changes,
                           total_closing=total_closing,
                           start=start, end=end)


# ─── BUDGET VS ACTUAL ─────────────────────────────────────
@reports_bp.route('/budget-vs-actual')
@login_required
def budget_vs_actual():
    """Compare budgeted amounts against actual for revenue/expense accounts."""
    year = request.args.get('year', date.today().year, type=int)
    start = date(year, 1, 1)
    end = date(year, 12, 31)

    accounts = Account.query.filter(
        Account.account_type.in_(['Revenue', 'Expense']),
        Account.is_active == True,
        Account.user_id == current_user.id
    ).order_by(Account.code).all()

    data = []
    for acct in accounts:
        # Budget total for the year
        budget_total = db.session.query(
            func.coalesce(func.sum(Budget.amount), 0)
        ).filter(
            Budget.account_id == acct.id,
            Budget.year == year,
            Budget.user_id == current_user.id,
        ).scalar() or 0
        budget_total = float(budget_total)

        if budget_total == 0:
            continue  # Skip accounts without budgets

        # Actual for the year
        debit, credit = get_account_balance(acct.id, start, end)
        if acct.account_type == 'Revenue':
            actual = float(credit - debit)
        else:
            actual = float(debit - credit)

        variance = actual - budget_total
        variance_pct = (variance / budget_total * 100) if budget_total != 0 else 0

        data.append({
            'account': acct,
            'budget': budget_total,
            'actual': actual,
            'variance': variance,
            'variance_pct': variance_pct,
        })

    current_year = date.today().year
    years = list(range(current_year - 2, current_year + 3))

    return render_template('reports/budget_vs_actual.html',
                           data=data, year=year, years=years)


# ─── CUSTOMER STATEMENT ───────────────────────────────────
@reports_bp.route('/customer-statement')
@login_required
def customer_statement():
    """Transaction history for a specific customer."""
    customer_id = request.args.get('customer_id', type=int)
    start, end = get_date_range()

    customers = Customer.query.filter_by(is_active=True, user_id=current_user.id).order_by(Customer.name).all()
    transactions = []
    selected_customer = None
    opening_balance = 0
    closing_balance = 0

    if customer_id:
        selected_customer = Customer.query.filter_by(id=customer_id, user_id=current_user.id).first()
        if selected_customer:
            # Invoices before start date = opening AR
            prior_invoices = Invoice.query.filter(
                Invoice.customer_id == customer_id,
                Invoice.date < start,
                Invoice.status != 'draft',
                Invoice.user_id == current_user.id,
            ).all()
            prior_payments = PaymentReceived.query.filter(
                PaymentReceived.date < start,
                PaymentReceived.user_id == current_user.id,
            ).all()
            # Simple calculation: sum of all invoices - payments for this customer
            prior_inv_total = sum(float(inv.total) for inv in prior_invoices)
            prior_pay_total = sum(float(p.amount) for p in prior_payments
                                  if p.invoice and p.invoice.customer_id == customer_id)
            opening_balance = prior_inv_total - prior_pay_total

            # Invoices in period
            invoices = Invoice.query.filter(
                Invoice.customer_id == customer_id,
                Invoice.date >= start,
                Invoice.date <= end,
                Invoice.status != 'draft',
                Invoice.user_id == current_user.id,
            ).order_by(Invoice.date).all()

            # Payments in period
            payments = PaymentReceived.query.filter(
                PaymentReceived.date >= start,
                PaymentReceived.date <= end,
                PaymentReceived.user_id == current_user.id,
            ).order_by(PaymentReceived.date).all()
            payments = [p for p in payments if p.invoice and p.invoice.customer_id == customer_id]

            running = opening_balance
            for inv in invoices:
                running += float(inv.total)
                transactions.append({
                    'date': inv.date,
                    'type': 'Invoice',
                    'reference': inv.invoice_number,
                    'description': f'Invoice to {selected_customer.name}',
                    'debit': float(inv.total),
                    'credit': 0,
                    'balance': running,
                })
            for pay in payments:
                running -= float(pay.amount)
                transactions.append({
                    'date': pay.date,
                    'type': 'Payment',
                    'reference': pay.payment_number,
                    'description': f'Payment received',
                    'debit': 0,
                    'credit': float(pay.amount),
                    'balance': running,
                })

            # Sort by date
            transactions.sort(key=lambda x: x['date'])
            # Recalculate running balance after sorting
            running = opening_balance
            for t in transactions:
                running += t['debit'] - t['credit']
                t['balance'] = running
            closing_balance = running

    return render_template('reports/customer_statement.html',
                           customers=customers, selected_customer=selected_customer,
                           customer_id=customer_id, transactions=transactions,
                           opening_balance=opening_balance,
                           closing_balance=closing_balance,
                           start=start, end=end)


# ─── VENDOR STATEMENT ─────────────────────────────────────
@reports_bp.route('/vendor-statement')
@login_required
def vendor_statement():
    """Transaction history for a specific vendor."""
    vendor_id = request.args.get('vendor_id', type=int)
    start, end = get_date_range()

    vendors = Vendor.query.filter_by(is_active=True, user_id=current_user.id).order_by(Vendor.name).all()
    transactions = []
    selected_vendor = None
    opening_balance = 0
    closing_balance = 0

    if vendor_id:
        selected_vendor = Vendor.query.filter_by(id=vendor_id, user_id=current_user.id).first()
        if selected_vendor:
            prior_bills = Bill.query.filter(
                Bill.vendor_id == vendor_id,
                Bill.date < start,
                Bill.status != 'draft',
                Bill.user_id == current_user.id,
            ).all()
            prior_payments = PaymentMade.query.filter(
                PaymentMade.date < start,
                PaymentMade.user_id == current_user.id,
            ).all()
            prior_bill_total = sum(float(b.total) for b in prior_bills)
            prior_pay_total = sum(float(p.amount) for p in prior_payments
                                  if p.bill and p.bill.vendor_id == vendor_id)
            opening_balance = prior_bill_total - prior_pay_total

            bills = Bill.query.filter(
                Bill.vendor_id == vendor_id,
                Bill.date >= start,
                Bill.date <= end,
                Bill.status != 'draft',
                Bill.user_id == current_user.id,
            ).order_by(Bill.date).all()

            payments = PaymentMade.query.filter(
                PaymentMade.date >= start,
                PaymentMade.date <= end,
                PaymentMade.user_id == current_user.id,
            ).order_by(PaymentMade.date).all()
            payments = [p for p in payments if p.bill and p.bill.vendor_id == vendor_id]

            running = opening_balance
            for bill in bills:
                running += float(bill.total)
                transactions.append({
                    'date': bill.date,
                    'type': 'Bill',
                    'reference': bill.bill_number,
                    'description': f'Bill from {selected_vendor.name}',
                    'debit': float(bill.total),
                    'credit': 0,
                    'balance': running,
                })
            for pay in payments:
                running -= float(pay.amount)
                transactions.append({
                    'date': pay.date,
                    'type': 'Payment',
                    'reference': pay.payment_number,
                    'description': f'Payment made',
                    'debit': 0,
                    'credit': float(pay.amount),
                    'balance': running,
                })

            transactions.sort(key=lambda x: x['date'])
            running = opening_balance
            for t in transactions:
                running += t['debit'] - t['credit']
                t['balance'] = running
            closing_balance = running

    return render_template('reports/vendor_statement.html',
                           vendors=vendors, selected_vendor=selected_vendor,
                           vendor_id=vendor_id, transactions=transactions,
                           opening_balance=opening_balance,
                           closing_balance=closing_balance,
                           start=start, end=end)
