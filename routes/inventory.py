from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database.models import db, Product, StockMovement, Account, Category, Invoice, InvoiceItem, Bill, BillItem, CompanySettings, log_activity
from datetime import date

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')


def _generate_sku():
    """Generate a unique SKU. Service businesses use SVC- prefix, product businesses use PRD-."""
    settings = CompanySettings.query.filter_by(user_id=current_user.id).first()
    prefix = 'SVC' if (settings and settings.business_type == 'service') else 'PRD'
    last = Product.query.filter_by(user_id=current_user.id).order_by(Product.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    while True:
        sku = f'{prefix}-{next_num:05d}'
        if not Product.query.filter_by(sku=sku, user_id=current_user.id).first():
            return sku
        next_num += 1


@inventory_bp.route('/')
@login_required
def index():
    products = Product.query.filter_by(user_id=current_user.id).order_by(Product.name).all()
    return render_template('inventory/index.html', products=products)


@inventory_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    settings = CompanySettings.query.filter_by(user_id=current_user.id).first()
    is_service_biz = settings and settings.business_type == 'service'

    if request.method == 'POST':
        category_id = request.form.get('category_id') or None
        item_type = 'service' if is_service_biz else request.form.get('item_type', 'product')
        is_service = (item_type == 'service')
        product = Product(
            sku=request.form['sku'],
            name=request.form['name'],
            description=request.form.get('description', ''),
            category_id=int(category_id) if category_id else None,
            unit=request.form.get('unit', 'pcs'),
            cost_price=float(request.form.get('cost_price', 0) or 0),
            selling_price=float(request.form.get('selling_price', 0) or 0),
            quantity_on_hand=float(request.form.get('quantity_on_hand', 0) or 0),
            reorder_level=float(request.form.get('reorder_level', 0) or 0),
            is_service=is_service,
            item_type=item_type,
            sub_category=request.form.get('sub_category', ''),
            revenue_type=request.form.get('revenue_type', ''),
            cost_behavior=request.form.get('cost_behavior', ''),
            tax_type=request.form.get('tax_type', 'taxable'),
            user_id=current_user.id,
        )

        # Set default accounts
        income_acct = Account.query.filter_by(code='4000', user_id=current_user.id).first()
        expense_acct = Account.query.filter_by(code='5000', user_id=current_user.id).first()
        asset_acct = Account.query.filter_by(code='1300', user_id=current_user.id).first()
        if income_acct:
            product.income_account_id = income_acct.id
        if expense_acct:
            product.expense_account_id = expense_acct.id
        if asset_acct:
            product.asset_account_id = asset_acct.id

        db.session.add(product)

        # Create initial stock movement if qty > 0 (product businesses only)
        if product.quantity_on_hand > 0 and not product.is_service and not is_service_biz:
            sm = StockMovement(
                product=product,
                date=date.today(),
                movement_type='in',
                quantity=product.quantity_on_hand,
                unit_cost=product.cost_price,
                reference='Opening Balance',
                notes='Initial stock entry',
                user_id=current_user.id,
            )
            db.session.add(sm)

        try:
            log_activity('create', 'Product', product.id, f'{product.sku} {product.name}',
                         f'Created product {product.sku} - {product.name}')
            db.session.commit()
            flash(f'Product "{product.name}" created.', 'success')
            return redirect(url_for('inventory.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')

    categories = Category.query.filter_by(is_active=True, user_id=current_user.id).order_by(Category.sort_order, Category.name).all()
    next_sku = _generate_sku()
    return render_template('inventory/form.html', product=None, categories=categories, next_sku=next_sku)


@inventory_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        product.sku = request.form['sku']
        product.name = request.form['name']
        product.description = request.form.get('description', '')
        category_id = request.form.get('category_id') or None
        product.category_id = int(category_id) if category_id else None
        product.unit = request.form.get('unit', 'pcs')
        product.cost_price = float(request.form.get('cost_price', 0) or 0)
        product.selling_price = float(request.form.get('selling_price', 0) or 0)
        product.reorder_level = float(request.form.get('reorder_level', 0) or 0)
        item_type = request.form.get('item_type', 'product')
        product.item_type = item_type
        product.is_service = (item_type == 'service')
        product.sub_category = request.form.get('sub_category', '')
        product.revenue_type = request.form.get('revenue_type', '')
        product.cost_behavior = request.form.get('cost_behavior', '')
        product.tax_type = request.form.get('tax_type', 'taxable')
        try:
            log_activity('update', 'Product', product.id, f'{product.sku} {product.name}',
                         f'Updated product {product.sku} - {product.name}')
            db.session.commit()
            flash(f'Product "{product.name}" updated.', 'success')
            return redirect(url_for('inventory.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')

    categories = Category.query.filter_by(is_active=True, user_id=current_user.id).order_by(Category.sort_order, Category.name).all()
    return render_template('inventory/form.html', product=product, categories=categories)


@inventory_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    log_activity('delete', 'Product', product.id, f'{product.sku} {product.name}',
                 f'Deleted product {product.sku} - {product.name}')
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted.', 'success')
    return redirect(url_for('inventory.index'))


# ─── STOCK MOVEMENTS ──────────────────────────────────────
@inventory_bp.route('/stock-movements')
@login_required
def stock_movements():
    # Filters
    product_id = request.args.get('product_id', type=int)
    movement_type = request.args.get('type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = StockMovement.query.filter_by(user_id=current_user.id)
    if product_id:
        query = query.filter_by(product_id=product_id)
    if movement_type:
        query = query.filter_by(movement_type=movement_type)
    if date_from:
        query = query.filter(StockMovement.date >= date.fromisoformat(date_from))
    if date_to:
        query = query.filter(StockMovement.date <= date.fromisoformat(date_to))

    movements = query.order_by(StockMovement.date.desc(), StockMovement.id.desc()).all()
    products = Product.query.filter_by(is_active=True, is_service=False, user_id=current_user.id).order_by(Product.name).all()
    return render_template('inventory/stock_movements.html', movements=movements, products=products,
                           filter_product_id=product_id, filter_type=movement_type,
                           filter_date_from=date_from, filter_date_to=date_to)


# ─── ADJUSTMENT REASON CATEGORIES ─────────────────────────
ADJUSTMENT_REASONS = [
    ('broken', 'Broken / Damaged'),
    ('lost', 'Lost / Missing'),
    ('expired', 'Expired'),
    ('returned', 'Customer Return'),
    ('correction', 'Count Correction'),
    ('theft', 'Theft / Shrinkage'),
    ('restock', 'Restock / Replenish'),
    ('production', 'Used in Production'),
    ('sample', 'Sample / Giveaway'),
    ('other', 'Other'),
]

@inventory_bp.route('/stock-adjustment', methods=['GET', 'POST'])
@login_required
def stock_adjustment():
    if request.method == 'POST':
        product_id = int(request.form['product_id'])
        product = Product.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()
        movement_type = request.form['movement_type']
        quantity = float(request.form['quantity'])
        reason = request.form.get('reason', 'other')
        reason_label = dict(ADJUSTMENT_REASONS).get(reason, reason)

        reference = request.form.get('reference', '').strip()
        if not reference:
            reference = f'Adjustment: {reason_label}'

        sm = StockMovement(
            product_id=product_id,
            date=date.fromisoformat(request.form['date']),
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=float(request.form.get('unit_cost', 0) or 0),
            reference=reference,
            notes=f'[{reason_label}] {request.form.get("notes", "").strip()}',
            user_id=current_user.id,
        )

        old_qty = float(product.quantity_on_hand or 0)
        if movement_type == 'in':
            product.quantity_on_hand = old_qty + float(quantity)
        elif movement_type == 'out':
            product.quantity_on_hand = old_qty - float(quantity)
        else:  # adjustment (set to exact)
            product.quantity_on_hand = float(quantity)

        db.session.add(sm)
        log_activity('create', 'Stock Adjustment', sm.id, f'{product.sku}',
                     f'Stock {movement_type} for {product.name}: {old_qty} → {float(product.quantity_on_hand)} ({reason_label}: {quantity} {product.unit})')
        db.session.commit()
        flash(f'Stock adjusted for "{product.name}": {old_qty} → {float(product.quantity_on_hand)} {product.unit} ({reason_label}).', 'success')
        return redirect(url_for('inventory.stock_movements'))

    products = Product.query.filter_by(is_active=True, is_service=False, user_id=current_user.id).order_by(Product.name).all()
    return render_template('inventory/adjustment.html', products=products, today=date.today(),
                           reasons=ADJUSTMENT_REASONS)


# ─── PER-PRODUCT STOCK HISTORY (AUDIT TRAIL) ─────────────
@inventory_bp.route('/product/<int:id>/history')
@login_required
def product_history(id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    movements = StockMovement.query.filter_by(
        product_id=id, user_id=current_user.id
    ).order_by(StockMovement.date.asc(), StockMovement.id.asc()).all()

    # Compute running balance
    running_balance = 0
    history = []
    for m in movements:
        qty = float(m.quantity)
        if m.movement_type == 'in':
            running_balance += qty
            direction = '+'
        elif m.movement_type == 'out':
            running_balance -= qty
            direction = '−'
        else:  # adjustment — set to
            running_balance = qty
            direction = '='

        # Try to resolve customer/vendor from reference
        customer_name = None
        vendor_name = None
        if m.reference and m.reference.startswith('INV-'):
            inv = Invoice.query.filter_by(invoice_number=m.reference, user_id=current_user.id).first()
            if inv and inv.customer:
                customer_name = inv.customer.name
        elif m.reference and m.reference.startswith('BILL-'):
            bill = Bill.query.filter_by(bill_number=m.reference, user_id=current_user.id).first()
            if bill and bill.vendor:
                vendor_name = bill.vendor.name
        elif m.notes:
            if 'Sale to ' in m.notes:
                customer_name = m.notes.split('Sale to ')[-1]
            elif 'Purchase from ' in m.notes:
                vendor_name = m.notes.split('Purchase from ')[-1]

        history.append({
            'id': m.id,
            'date': m.date,
            'type': m.movement_type,
            'direction': direction,
            'quantity': qty,
            'unit_cost': float(m.unit_cost or 0),
            'total_value': qty * float(m.unit_cost or 0),
            'running_balance': running_balance,
            'reference': m.reference or '—',
            'notes': m.notes or '',
            'customer': customer_name,
            'vendor': vendor_name,
            'created_at': m.created_at,
        })

    # Reverse for display (newest first) but keep running balances correct
    history.reverse()

    return render_template('inventory/product_history.html',
                           product=product, history=history,
                           current_stock=float(product.quantity_on_hand))
