from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.models import db, Customer, log_activity

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')


@customers_bp.route('/')
@login_required
def index():
    query = Customer.query.filter_by(user_id=current_user.id)

    # --- Filters ---
    search_q = request.args.get('q', '').strip()
    filter_city = request.args.get('city', '')
    filter_balance = request.args.get('balance', '')     # 'has' | 'zero'
    filter_status = request.args.get('status', '')       # 'active' | 'inactive'

    if search_q:
        like = f'%{search_q}%'
        query = query.filter(
            db.or_(
                Customer.name.ilike(like),
                Customer.email.ilike(like),
                Customer.phone.ilike(like),
            )
        )
    if filter_city:
        query = query.filter(Customer.city == filter_city)
    if filter_balance == 'has':
        query = query.filter(Customer.balance != 0)
    elif filter_balance == 'zero':
        query = query.filter(Customer.balance == 0)
    if filter_status == 'active':
        query = query.filter(Customer.is_active == True)
    elif filter_status == 'inactive':
        query = query.filter(Customer.is_active == False)

    customers = query.order_by(Customer.name).all()

    # Distinct cities for the dropdown (one cheap query)
    cities = db.session.query(Customer.city)\
        .filter(Customer.user_id == current_user.id, Customer.city != '', Customer.city.isnot(None))\
        .distinct().order_by(Customer.city).all()
    cities = [c[0] for c in cities]

    return render_template('customers/index.html',
                           customers=customers, cities=cities,
                           search_q=search_q, filter_city=filter_city,
                           filter_balance=filter_balance, filter_status=filter_status)


@customers_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        customer = Customer(
            name=request.form['name'],
            email=request.form.get('email', ''),
            phone=request.form.get('phone', ''),
            address=request.form.get('address', ''),
            city=request.form.get('city', ''),
            tax_id=request.form.get('tax_id', ''),
            credit_limit=float(request.form.get('credit_limit', 0) or 0),
            notes=request.form.get('notes', ''),
            user_id=current_user.id,
        )
        db.session.add(customer)
        db.session.flush()
        log_activity('create', 'Customer', customer.id, customer.name, f'Created customer "{customer.name}"')
        db.session.commit()
        flash(f'Customer "{customer.name}" created.', 'success')
        return redirect(url_for('customers.index'))
    return render_template('customers/form.html', customer=None)


@customers_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    customer = Customer.query.get_or_404(id)
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.email = request.form.get('email', '')
        customer.phone = request.form.get('phone', '')
        customer.address = request.form.get('address', '')
        customer.city = request.form.get('city', '')
        customer.tax_id = request.form.get('tax_id', '')
        customer.credit_limit = float(request.form.get('credit_limit', 0) or 0)
        customer.notes = request.form.get('notes', '')
        log_activity('update', 'Customer', customer.id, customer.name, f'Updated customer "{customer.name}"')
        db.session.commit()
        flash(f'Customer "{customer.name}" updated.', 'success')
        return redirect(url_for('customers.index'))
    return render_template('customers/form.html', customer=customer)


@customers_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    customer = Customer.query.get_or_404(id)
    if customer.invoices.count() > 0:
        flash('Cannot delete customer with existing invoices.', 'warning')
        return redirect(url_for('customers.index'))
    db.session.delete(customer)
    log_activity('delete', 'Customer', customer.id, customer.name, f'Deleted customer "{customer.name}"')
    db.session.commit()
    flash('Customer deleted.', 'success')
    return redirect(url_for('customers.index'))
