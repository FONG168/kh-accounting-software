from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.models import db, Vendor, log_activity

vendors_bp = Blueprint('vendors', __name__, url_prefix='/vendors')


@vendors_bp.route('/')
@login_required
def index():
    query = Vendor.query.filter_by(user_id=current_user.id)

    # --- Filters ---
    search_q = request.args.get('q', '').strip()
    filter_city = request.args.get('city', '')
    filter_balance = request.args.get('balance', '')     # 'has' | 'zero'
    filter_status = request.args.get('status', '')       # 'active' | 'inactive'

    if search_q:
        like = f'%{search_q}%'
        query = query.filter(
            db.or_(
                Vendor.name.ilike(like),
                Vendor.email.ilike(like),
                Vendor.phone.ilike(like),
            )
        )
    if filter_city:
        query = query.filter(Vendor.city == filter_city)
    if filter_balance == 'has':
        query = query.filter(Vendor.balance != 0)
    elif filter_balance == 'zero':
        query = query.filter(Vendor.balance == 0)
    if filter_status == 'active':
        query = query.filter(Vendor.is_active == True)
    elif filter_status == 'inactive':
        query = query.filter(Vendor.is_active == False)

    vendors = query.order_by(Vendor.name).all()

    # Distinct cities for the dropdown (one cheap query)
    cities = db.session.query(Vendor.city)\
        .filter(Vendor.user_id == current_user.id, Vendor.city != '', Vendor.city.isnot(None))\
        .distinct().order_by(Vendor.city).all()
    cities = [c[0] for c in cities]

    return render_template('vendors/index.html',
                           vendors=vendors, cities=cities,
                           search_q=search_q, filter_city=filter_city,
                           filter_balance=filter_balance, filter_status=filter_status)


@vendors_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        vendor = Vendor(
            name=request.form['name'],
            email=request.form.get('email', ''),
            phone=request.form.get('phone', ''),
            address=request.form.get('address', ''),
            city=request.form.get('city', ''),
            tax_id=request.form.get('tax_id', ''),
            notes=request.form.get('notes', ''),
            user_id=current_user.id,
        )
        db.session.add(vendor)
        db.session.flush()
        log_activity('create', 'Vendor', vendor.id, vendor.name, f'Created vendor "{vendor.name}"')
        db.session.commit()
        flash(f'Vendor "{vendor.name}" created.', 'success')
        return redirect(url_for('vendors.index'))
    return render_template('vendors/form.html', vendor=None)


@vendors_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    vendor = Vendor.query.get_or_404(id)
    if request.method == 'POST':
        vendor.name = request.form['name']
        vendor.email = request.form.get('email', '')
        vendor.phone = request.form.get('phone', '')
        vendor.address = request.form.get('address', '')
        vendor.city = request.form.get('city', '')
        vendor.tax_id = request.form.get('tax_id', '')
        vendor.notes = request.form.get('notes', '')
        log_activity('update', 'Vendor', vendor.id, vendor.name, f'Updated vendor "{vendor.name}"')
        db.session.commit()
        flash(f'Vendor "{vendor.name}" updated.', 'success')
        return redirect(url_for('vendors.index'))
    return render_template('vendors/form.html', vendor=vendor)


@vendors_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    vendor = Vendor.query.get_or_404(id)
    if vendor.bills.count() > 0:
        flash('Cannot delete vendor with existing bills.', 'warning')
        return redirect(url_for('vendors.index'))
    log_activity('delete', 'Vendor', vendor.id, vendor.name, f'Deleted vendor "{vendor.name}"')
    db.session.delete(vendor)
    db.session.commit()
    flash('Vendor deleted.', 'success')
    return redirect(url_for('vendors.index'))
