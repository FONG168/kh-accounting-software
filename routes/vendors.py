from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.models import db, Vendor, log_activity

vendors_bp = Blueprint('vendors', __name__, url_prefix='/vendors')


@vendors_bp.route('/')
@login_required
def index():
    vendors = Vendor.query.filter_by(user_id=current_user.id).order_by(Vendor.name).all()
    return render_template('vendors/index.html', vendors=vendors)


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
