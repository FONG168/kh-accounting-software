from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database.models import db, Category, log_activity

categories_bp = Blueprint('categories', __name__, url_prefix='/categories')


@categories_bp.route('/')
@login_required
def index():
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.sort_order, Category.name).all()
    return render_template('categories/index.html', categories=categories)


@categories_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Category name is required.', 'warning')
            return redirect(url_for('categories.create'))

        existing = Category.query.filter(Category.user_id == current_user.id, db.func.lower(Category.name) == name.lower()).first()
        if existing:
            flash(f'Category "{name}" already exists.', 'warning')
            return redirect(url_for('categories.create'))

        parent_id = request.form.get('parent_id') or None
        max_order = db.session.query(db.func.coalesce(db.func.max(Category.sort_order), 0)).filter(Category.user_id == current_user.id).scalar()

        cat = Category(
            name=name,
            description=request.form.get('description', ''),
            category_type=request.form.get('category_type', 'product'),
            parent_id=int(parent_id) if parent_id else None,
            is_custom=True,
            sort_order=max_order + 1,
            user_id=current_user.id,
        )
        db.session.add(cat)
        db.session.flush()
        log_activity('create', 'Category', cat.id, cat.name, f'Created category "{cat.name}"')
        db.session.commit()
        flash(f'Category "{cat.name}" created.', 'success')
        return redirect(url_for('categories.index'))

    parents = Category.query.filter_by(parent_id=None, user_id=current_user.id).order_by(Category.sort_order, Category.name).all()
    return render_template('categories/form.html', category=None, parents=parents)


@categories_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    cat = Category.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Category name is required.', 'warning')
            return redirect(url_for('categories.edit', id=id))

        dup = Category.query.filter(
            Category.user_id == current_user.id,
            db.func.lower(Category.name) == name.lower(),
            Category.id != id
        ).first()
        if dup:
            flash(f'Category "{name}" already exists.', 'warning')
            return redirect(url_for('categories.edit', id=id))

        cat.name = name
        cat.description = request.form.get('description', '')
        cat.category_type = request.form.get('category_type', cat.category_type or 'product')
        parent_id = request.form.get('parent_id') or None
        cat.parent_id = int(parent_id) if parent_id else None
        cat.is_active = 'is_active' in request.form
        log_activity('update', 'Category', cat.id, cat.name, f'Updated category "{cat.name}"')
        db.session.commit()
        flash(f'Category "{cat.name}" updated.', 'success')
        return redirect(url_for('categories.index'))

    parents = Category.query.filter(
        Category.user_id == current_user.id,
        Category.parent_id == None,
        Category.id != id
    ).order_by(Category.sort_order, Category.name).all()
    return render_template('categories/form.html', category=cat, parents=parents)


@categories_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    cat = Category.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    product_count = cat.products.count()
    child_count = len(cat.children)
    if product_count > 0:
        flash(f'Cannot delete "{cat.name}" — {product_count} product(s) are using it.', 'warning')
        return redirect(url_for('categories.index'))
    if child_count > 0:
        flash(f'Cannot delete "{cat.name}" — it has {child_count} sub-categories.', 'warning')
        return redirect(url_for('categories.index'))
    log_activity('delete', 'Category', cat.id, cat.name, f'Deleted category "{cat.name}"')
    db.session.delete(cat)
    db.session.commit()
    flash(f'Category "{cat.name}" deleted.', 'success')
    return redirect(url_for('categories.index'))


@categories_bp.route('/api/list')
@login_required
def api_list():
    """JSON endpoint for dynamic dropdowns."""
    cats = Category.query.filter_by(is_active=True, user_id=current_user.id).order_by(Category.sort_order, Category.name).all()
    return jsonify([{'id': c.id, 'name': c.name, 'parent_id': c.parent_id, 'category_type': c.category_type or 'product'} for c in cats])
