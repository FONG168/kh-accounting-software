from flask_login import login_required, current_user
from flask import Blueprint, render_template, jsonify, request
from database.models import (db, Account, Invoice, Bill, Expense, Product,
                             Customer, Vendor, JournalEntry, PaymentReceived,
                             PaymentMade, CompanySettings, Announcement)
from datetime import date, timedelta, datetime
from sqlalchemy import func, desc
import json

dashboard_bp = Blueprint('dashboard', __name__)


def _month_range(y, m):
    """Return (first_day, last_day) for a given year/month."""
    first = date(y, m, 1)
    if m == 12:
        last = date(y + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(y, m + 1, 1) - timedelta(days=1)
    return first, last


def _prev_month(y, m):
    """Return (year, month) of previous month."""
    m -= 1
    while m <= 0:
        m += 12
        y -= 1
    return y, m


@dashboard_bp.route('/')
@login_required
def index():
    today = date.today()
    now = datetime.now()
    month_start = date(today.year, today.month, 1)
    year_start = date(today.year, 1, 1)

    # Greeting based on time of day
    hour = now.hour
    if hour < 12:
        greeting = 'Good morning'
    elif hour < 17:
        greeting = 'Good afternoon'
    else:
        greeting = 'Good evening'

    # Company settings
    settings = CompanySettings.query.filter_by(user_id=current_user.id).first()
    currency = settings.currency_symbol if settings else '$'

    # ─── KEY METRICS (current month) ──────────────────
    monthly_revenue = float(db.session.query(
        func.coalesce(func.sum(Invoice.total), 0)
    ).filter(
        Invoice.user_id == current_user.id,
        Invoice.date >= month_start, Invoice.date <= today,
        Invoice.status != 'draft'
    ).scalar())

    monthly_expenses_bills = float(db.session.query(
        func.coalesce(func.sum(Bill.total), 0)
    ).filter(
        Bill.user_id == current_user.id,
        Bill.date >= month_start, Bill.date <= today,
        Bill.status != 'draft'
    ).scalar())

    monthly_expenses_petty = float(db.session.query(
        func.coalesce(func.sum(Expense.amount), 0)
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= month_start, Expense.date <= today
    ).scalar())

    monthly_expenses = monthly_expenses_bills + monthly_expenses_petty

    total_receivables = float(db.session.query(
        func.coalesce(func.sum(Invoice.balance_due), 0)
    ).filter(
        Invoice.user_id == current_user.id,
        Invoice.status.in_(['sent', 'owed', 'partial', 'overdue']),
        Invoice.balance_due > 0
    ).scalar())

    total_payables = float(db.session.query(
        func.coalesce(func.sum(Bill.balance_due), 0)
    ).filter(
        Bill.user_id == current_user.id,
        Bill.status.in_(['received', 'partial', 'overdue', 'owed']),
        Bill.balance_due > 0
    ).scalar())

    products = Product.query.filter_by(user_id=current_user.id, is_active=True, is_service=False).all()
    inventory_value = float(sum(p.quantity_on_hand * p.cost_price for p in products))

    cash_account = Account.query.filter_by(user_id=current_user.id, code='1000').first()
    bank_account = Account.query.filter_by(user_id=current_user.id, code='1100').first()
    petty_cash_account = Account.query.filter_by(user_id=current_user.id, code='1050').first()
    cash_balance = 0
    cash_on_hand = 0
    bank_balance = 0
    petty_cash_balance = 0
    if cash_account:
        cash_on_hand = float(cash_account.get_balance(user_id=current_user.id))
        cash_balance += cash_on_hand
    if bank_account:
        bank_balance = float(bank_account.get_balance(user_id=current_user.id))
        cash_balance += bank_balance
    if petty_cash_account:
        petty_cash_balance = float(petty_cash_account.get_balance(user_id=current_user.id))
        cash_balance += petty_cash_balance

    net_income = monthly_revenue - monthly_expenses
    profit_margin = (net_income / monthly_revenue * 100) if monthly_revenue > 0 else 0

    # ─── PREVIOUS MONTH METRICS (for MoM comparison) ──
    py, pm = _prev_month(today.year, today.month)
    prev_start, prev_end = _month_range(py, pm)

    prev_revenue = float(db.session.query(
        func.coalesce(func.sum(Invoice.total), 0)
    ).filter(
        Invoice.user_id == current_user.id,
        Invoice.date >= prev_start, Invoice.date <= prev_end,
        Invoice.status != 'draft'
    ).scalar())

    prev_expenses_bills = float(db.session.query(
        func.coalesce(func.sum(Bill.total), 0)
    ).filter(
        Bill.user_id == current_user.id,
        Bill.date >= prev_start, Bill.date <= prev_end,
        Bill.status != 'draft'
    ).scalar())

    prev_expenses_petty = float(db.session.query(
        func.coalesce(func.sum(Expense.amount), 0)
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= prev_start, Expense.date <= prev_end
    ).scalar())

    prev_expenses = prev_expenses_bills + prev_expenses_petty

    # Growth percentages
    def pct_change(current, previous):
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return ((current - previous) / abs(previous)) * 100

    revenue_growth = pct_change(monthly_revenue, prev_revenue)
    expense_growth = pct_change(monthly_expenses, prev_expenses)

    # ─── FINANCIAL HEALTH RATIOS ──────────────────────
    # Current Assets (cash, bank, petty cash, receivables, inventory)
    current_assets = cash_balance + total_receivables + inventory_value
    # Current Liabilities (payables)
    current_liabilities = total_payables if total_payables > 0 else 0
    # Quick Assets (current assets minus inventory)
    quick_assets = cash_balance + total_receivables

    current_ratio = current_assets / current_liabilities if current_liabilities > 0 else 0
    quick_ratio = quick_assets / current_liabilities if current_liabilities > 0 else 0
    working_capital = current_assets - current_liabilities

    # ─── CHART DATA: Monthly Revenue & Expenses (last 6 months) ───
    chart_labels = []
    chart_revenue = []
    chart_expenses = []
    chart_profit = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        m_start, m_end = _month_range(y, m)
        chart_labels.append(m_start.strftime('%b %Y'))

        rev = float(db.session.query(
            func.coalesce(func.sum(Invoice.total), 0)
        ).filter(
            Invoice.user_id == current_user.id,
            Invoice.date >= m_start, Invoice.date <= m_end,
            Invoice.status != 'draft'
        ).scalar())
        chart_revenue.append(rev)

        exp_b = float(db.session.query(
            func.coalesce(func.sum(Bill.total), 0)
        ).filter(
            Bill.user_id == current_user.id,
            Bill.date >= m_start, Bill.date <= m_end,
            Bill.status != 'draft'
        ).scalar())
        exp_p = float(db.session.query(
            func.coalesce(func.sum(Expense.amount), 0)
        ).filter(
            Expense.user_id == current_user.id,
            Expense.date >= m_start, Expense.date <= m_end
        ).scalar())
        exp = exp_b + exp_p
        chart_expenses.append(exp)
        chart_profit.append(rev - exp)

    # ─── CHART DATA: Expense Breakdown by Category (this year) ───
    expense_cats = db.session.query(
        Expense.category, func.sum(Expense.amount)
    ).filter(Expense.user_id == current_user.id, Expense.date >= year_start).group_by(Expense.category).all()
    expense_cat_labels = [c[0] or 'Uncategorized' for c in expense_cats]
    expense_cat_values = [float(c[1]) for c in expense_cats]

    # ─── CHART DATA: Receivables vs Payables ─────────
    ar_vs_ap = {
        'receivables': float(total_receivables),
        'payables': float(total_payables)
    }

    # ─── CHART DATA: Revenue vs Expenses (Year-to-Date) ──
    ytd_revenue = float(db.session.query(
        func.coalesce(func.sum(Invoice.total), 0)
    ).filter(
        Invoice.user_id == current_user.id,
        Invoice.date >= year_start, Invoice.date <= today,
        Invoice.status != 'draft'
    ).scalar())

    ytd_expenses_bills = float(db.session.query(
        func.coalesce(func.sum(Bill.total), 0)
    ).filter(
        Bill.user_id == current_user.id,
        Bill.date >= year_start, Bill.date <= today,
        Bill.status != 'draft'
    ).scalar())
    ytd_expenses_petty = float(db.session.query(
        func.coalesce(func.sum(Expense.amount), 0)
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= year_start, Expense.date <= today
    ).scalar())
    ytd_expenses = ytd_expenses_bills + ytd_expenses_petty

    # ─── CHART DATA: Cash Flow (payments in vs out last 6 months) ──
    cf_in_data = []
    cf_out_data = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        m_start, m_end = _month_range(y, m)

        cash_in = float(db.session.query(
            func.coalesce(func.sum(PaymentReceived.amount), 0)
        ).filter(
            PaymentReceived.user_id == current_user.id,
            PaymentReceived.date >= m_start,
            PaymentReceived.date <= m_end
        ).scalar())
        cf_in_data.append(cash_in)

        cash_out_bills = float(db.session.query(
            func.coalesce(func.sum(PaymentMade.amount), 0)
        ).filter(
            PaymentMade.user_id == current_user.id,
            PaymentMade.date >= m_start,
            PaymentMade.date <= m_end
        ).scalar())
        cash_out_petty = float(db.session.query(
            func.coalesce(func.sum(Expense.amount), 0)
        ).filter(
            Expense.user_id == current_user.id,
            Expense.date >= m_start,
            Expense.date <= m_end
        ).scalar())
        cf_out_data.append(cash_out_bills + cash_out_petty)

    # ─── TOP CUSTOMERS BY REVENUE (YTD) ──────────────
    top_customers = db.session.query(
        Customer.name,
        func.sum(Invoice.total).label('total_revenue'),
        func.count(Invoice.id).label('invoice_count')
    ).join(Invoice, Invoice.customer_id == Customer.id).filter(
        Customer.user_id == current_user.id,
        Invoice.user_id == current_user.id,
        Invoice.date >= year_start,
        Invoice.status != 'draft'
    ).group_by(Customer.id, Customer.name).order_by(
        desc('total_revenue')
    ).limit(5).all()

    # ─── RECENT ACTIVITY ──────────────────────────────
    recent_invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.date.desc()).limit(5).all()
    recent_bills = Bill.query.filter_by(user_id=current_user.id).order_by(Bill.date.desc()).limit(5).all()
    recent_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).limit(5).all()

    # ─── KPI DRILL-DOWN DATA ──────────────────────────
    # Expenses (MTD) - bills + petty cash this month
    mtd_bills = Bill.query.filter(
        Bill.user_id == current_user.id,
        Bill.date >= month_start, Bill.date <= today,
        Bill.status != 'draft'
    ).order_by(Bill.date.desc()).all()
    mtd_petty = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= month_start, Expense.date <= today
    ).order_by(Expense.date.desc()).all()

    # Receivables - outstanding invoices
    outstanding_invoices = Invoice.query.filter(
        Invoice.user_id == current_user.id,
        Invoice.status.in_(['sent', 'owed', 'partial', 'overdue']),
        Invoice.balance_due > 0.01
    ).order_by(Invoice.date.desc()).all()

    # Cash & Bank - recent cash movements (payments in, out, expenses)
    cash_payments_in = PaymentReceived.query.filter_by(user_id=current_user.id).order_by(
        PaymentReceived.date.desc()
    ).limit(15).all()
    cash_payments_out = PaymentMade.query.filter_by(user_id=current_user.id).order_by(
        PaymentMade.date.desc()
    ).limit(15).all()
    cash_petty_out = Expense.query.filter_by(user_id=current_user.id).order_by(
        Expense.date.desc()
    ).limit(15).all()

    # ─── LOW STOCK ALERT ──────────────────────────────
    low_stock = Product.query.filter(
        Product.user_id == current_user.id,
        Product.is_service == False,
        Product.is_active == True,
        Product.reorder_level > 0,
        Product.quantity_on_hand <= Product.reorder_level
    ).order_by(Product.quantity_on_hand).limit(5).all()

    # ─── OVERDUE INVOICES ─────────────────────────────
    stale_invoices = Invoice.query.filter(
        Invoice.user_id == current_user.id,
        Invoice.status.in_(['sent', 'owed', 'partial']),
        Invoice.due_date < today,
        Invoice.balance_due > 0.01
    ).all()
    for inv in stale_invoices:
        inv.status = 'overdue'
    if stale_invoices:
        db.session.commit()

    overdue_invoices = Invoice.query.filter(
        Invoice.user_id == current_user.id,
        Invoice.status == 'overdue',
        Invoice.balance_due > 0.01
    ).order_by(Invoice.due_date).limit(5).all()

    # ─── OVERDUE / UPCOMING BILLS ─────────────────────
    stale_bills = Bill.query.filter(
        Bill.user_id == current_user.id,
        Bill.status.in_(['received', 'owed', 'partial']),
        Bill.due_date < today,
        Bill.balance_due > 0.01
    ).all()
    for b in stale_bills:
        b.status = 'overdue'
    if stale_bills:
        db.session.commit()

    overdue_bills = Bill.query.filter(
        Bill.user_id == current_user.id,
        Bill.status == 'overdue',
        Bill.balance_due > 0.01
    ).order_by(Bill.due_date).limit(5).all()

    upcoming_bills = Bill.query.filter(
        Bill.user_id == current_user.id,
        Bill.status.in_(['received', 'owed', 'partial']),
        Bill.due_date != None,
        Bill.due_date >= today,
        Bill.due_date <= today + timedelta(days=7),
        Bill.balance_due > 0.01
    ).order_by(Bill.due_date).limit(5).all()

    # ─── COUNTS ───────────────────────────────────────
    customer_count = Customer.query.filter_by(user_id=current_user.id, is_active=True).count()
    vendor_count = Vendor.query.filter_by(user_id=current_user.id, is_active=True).count()
    product_count = Product.query.filter_by(user_id=current_user.id, is_active=True).count()

    total_invoices_mtd = Invoice.query.filter(
        Invoice.user_id == current_user.id,
        Invoice.date >= month_start, Invoice.status != 'draft'
    ).count()
    total_bills_mtd = Bill.query.filter(
        Bill.user_id == current_user.id,
        Bill.date >= month_start, Bill.status != 'draft'
    ).count()

    # ── Active Announcements from Admin ──
    from sqlalchemy import or_
    active_announcements = Announcement.query.filter(
        Announcement.is_active == True,
        or_(Announcement.expires_at.is_(None), Announcement.expires_at >= datetime.utcnow())
    ).order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc()).all()

    return render_template('dashboard.html',
                           greeting=greeting,
                           user=current_user,
                           currency=currency,
                           monthly_revenue=monthly_revenue,
                           monthly_expenses=monthly_expenses,
                           total_receivables=total_receivables,
                           total_payables=total_payables,
                           inventory_value=inventory_value,
                           cash_balance=cash_balance,
                           cash_on_hand=cash_on_hand,
                           bank_balance=bank_balance,
                           petty_cash_balance=petty_cash_balance,
                           net_income=net_income,
                           profit_margin=profit_margin,
                           revenue_growth=revenue_growth,
                           expense_growth=expense_growth,
                           # Financial ratios
                           current_ratio=current_ratio,
                           quick_ratio=quick_ratio,
                           working_capital=working_capital,
                           # Activity data
                           recent_invoices=recent_invoices,
                           recent_bills=recent_bills,
                           recent_expenses=recent_expenses,
                           low_stock=low_stock,
                           overdue_invoices=overdue_invoices,
                           overdue_bills=overdue_bills,
                           upcoming_bills=upcoming_bills,
                           top_customers=top_customers,
                           # Counts
                           customer_count=customer_count,
                           vendor_count=vendor_count,
                           product_count=product_count,
                           total_invoices_mtd=total_invoices_mtd,
                           total_bills_mtd=total_bills_mtd,
                           # KPI drill-down
                           mtd_bills=mtd_bills,
                           mtd_petty=mtd_petty,
                           outstanding_invoices=outstanding_invoices,
                           cash_payments_in=cash_payments_in,
                           cash_payments_out=cash_payments_out,
                           cash_petty_out=cash_petty_out,
                           today=today,
                           # Chart data (JSON-safe)
                           chart_labels=json.dumps(chart_labels),
                           chart_revenue=json.dumps(chart_revenue),
                           chart_expenses=json.dumps(chart_expenses),
                           chart_profit=json.dumps(chart_profit),
                           expense_cat_labels=json.dumps(expense_cat_labels),
                           expense_cat_values=json.dumps(expense_cat_values),
                           ar_vs_ap=json.dumps(ar_vs_ap),
                           ytd_revenue=float(ytd_revenue),
                           ytd_expenses=float(ytd_expenses),
                           cf_in_data=json.dumps(cf_in_data),
                           cf_out_data=json.dumps(cf_out_data),
                           announcements=active_announcements)


@dashboard_bp.route('/api/search')
@login_required
def api_search():
    """Global search endpoint for the command palette."""
    q = request.args.get('q', '').strip().lower()
    if len(q) < 2:
        return jsonify([])

    results = []
    # Customers
    customers = Customer.query.filter(Customer.user_id == current_user.id, Customer.name.ilike(f'%{q}%')).limit(5).all()
    for c in customers:
        results.append({'icon': 'bi-people', 'label': c.name, 'type': 'Customer',
                        'url': f'/customers/{c.id}/edit'})
    # Vendors
    vendors = Vendor.query.filter(Vendor.user_id == current_user.id, Vendor.name.ilike(f'%{q}%')).limit(5).all()
    for v in vendors:
        results.append({'icon': 'bi-truck', 'label': v.name, 'type': 'Vendor',
                        'url': f'/vendors/{v.id}/edit'})
    # Invoices
    invoices = Invoice.query.filter(Invoice.user_id == current_user.id, Invoice.invoice_number.ilike(f'%{q}%')).limit(5).all()
    for inv in invoices:
        results.append({'icon': 'bi-receipt', 'label': f'{inv.invoice_number} – {inv.total:,.2f}',
                        'type': 'Invoice', 'url': f'/sales/{inv.id}'})
    # Bills
    bills = Bill.query.filter(Bill.user_id == current_user.id, Bill.bill_number.ilike(f'%{q}%')).limit(5).all()
    for b in bills:
        results.append({'icon': 'bi-bag', 'label': f'{b.bill_number} – {b.total:,.2f}',
                        'type': 'Bill', 'url': f'/purchases/{b.id}'})
    # Products
    prods = Product.query.filter(Product.user_id == current_user.id, Product.name.ilike(f'%{q}%')).limit(5).all()
    for p in prods:
        results.append({'icon': 'bi-box-seam', 'label': p.name, 'type': 'Product',
                        'url': f'/inventory/{p.id}/edit'})

    return jsonify(results)
