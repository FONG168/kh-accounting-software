from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from database.models import db, CompanySettings, Category, Account, Product, log_activity
from database.firebase_sync import full_backup, full_restore, is_enabled as firebase_enabled
import os, uuid


def _seed_default_and_ifrs_accounts_for_user(user_id):
    """Seed default + IFRS accounts for a user if they have none yet."""
    if Account.query.filter_by(user_id=user_id).first() is not None:
        return
    from app import DEFAULT_ACCOUNTS, IFRS_ACCOUNTS
    for acct in DEFAULT_ACCOUNTS + IFRS_ACCOUNTS:
        db.session.add(Account(
            code=acct['code'],
            name=acct['name'],
            account_type=acct['account_type'],
            sub_type=acct.get('sub_type', ''),
            normal_balance=acct.get('normal_balance', 'debit'),
            is_system=True,
            user_id=user_id,
        ))
    db.session.commit()

setup_bp = Blueprint('setup', __name__, url_prefix='/setup')

# ─── INDUSTRY DEFINITIONS ─────────────────────────────────────────────
# Each industry has: display name, icon, description, default categories,
# and extra Chart-of-Accounts entries unique to that trade.
INDUSTRIES = {
    'retail': {
        'name': 'Retail / General Trade',
        'icon': 'bi-shop',
        'business_type': 'product',
        'desc': 'Buy and sell physical goods — shops, stores, e-commerce.',
        'categories': [
            # Products (Inventory)
            {'name': 'Electronics', 'type': 'product'},
            {'name': 'Clothing & Apparel', 'type': 'product'},
            {'name': 'Footwear', 'type': 'product'},
            {'name': 'Accessories', 'type': 'product'},
            {'name': 'Bags & Luggage', 'type': 'product'},
            {'name': 'Home & Garden', 'type': 'product'},
            {'name': 'Health & Beauty', 'type': 'product'},
            {'name': 'Toys & Games', 'type': 'product'},
            {'name': 'Sports & Outdoors', 'type': 'product'},
            {'name': 'Books & Stationery', 'type': 'product'},
            {'name': 'Food & Grocery', 'type': 'product'},
            {'name': 'Beverages', 'type': 'product'},
            {'name': 'Pet Supplies', 'type': 'product'},
            {'name': 'Automotive Parts', 'type': 'product'},
            {'name': 'Office Supplies', 'type': 'product'},
            {'name': 'Consumer Products', 'type': 'product'},
            {'name': 'Household Items', 'type': 'product'},
            # Services (Non-Inventory)
            {'name': 'Delivery Service', 'type': 'service'},
            {'name': 'Installation Service', 'type': 'service'},
            {'name': 'Warranty Service', 'type': 'service'},
            {'name': 'Gift Wrapping Service', 'type': 'service'},
            {'name': 'Other', 'type': 'product'},
        ],
        'extra_accounts': [
            {'code': '4150', 'name': 'Sales Returns & Allowances', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'debit'},
            {'code': '6050', 'name': 'Shipping & Delivery', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
            {'code': '6055', 'name': 'Packaging Supplies', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
        ],
    },
    'fnb': {
        'name': 'Food & Beverage (F&B)',
        'icon': 'bi-cup-hot',
        'business_type': 'product',
        'desc': 'Restaurants, cafés, bakeries, cloud kitchens, catering.',
        'categories': [
            # Products (Inventory)
            {'name': 'Raw Ingredients', 'type': 'product'},
            {'name': 'Vegetables & Herbs', 'type': 'product'},
            {'name': 'Meat & Seafood', 'type': 'product'},
            {'name': 'Dairy & Eggs', 'type': 'product'},
            {'name': 'Sauces & Condiments', 'type': 'product'},
            {'name': 'Bakery Supplies', 'type': 'product'},
            {'name': 'Beverages', 'type': 'product'},
            {'name': 'Frozen Foods', 'type': 'product'},
            {'name': 'Dry Goods & Grains', 'type': 'product'},
            {'name': 'Packaging & Takeaway', 'type': 'product'},
            {'name': 'Cleaning Supplies', 'type': 'product'},
            {'name': 'Kitchen Equipment', 'type': 'product'},
            {'name': 'Tableware & Utensils', 'type': 'product'},
            # Services (Non-Inventory)
            {'name': 'Catering Service', 'type': 'service'},
            {'name': 'Event Service', 'type': 'service'},
            {'name': 'Service Charge', 'type': 'service'},
            {'name': 'Delivery Fee', 'type': 'service'},
            {'name': 'Other', 'type': 'product'},
        ],
        'extra_accounts': [
            {'code': '4150', 'name': 'Dine-in Revenue', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '4160', 'name': 'Takeaway / Delivery Revenue', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '4170', 'name': 'Catering Revenue', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '5100', 'name': 'Food Cost', 'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
            {'code': '5200', 'name': 'Beverage Cost', 'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
            {'code': '6050', 'name': 'Kitchen Supplies', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
            {'code': '6055', 'name': 'Delivery & Platform Fees', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
        ],
    },
    'restaurant': {
        'name': 'Restaurant / Bar',
        'icon': 'bi-egg-fried',
        'business_type': 'product',
        'desc': 'Full-service restaurants, bars, pubs, lounges.',
        'categories': [
            # Products (Inventory)
            {'name': 'Raw Ingredients', 'type': 'product'},
            {'name': 'Meat & Poultry', 'type': 'product'},
            {'name': 'Seafood', 'type': 'product'},
            {'name': 'Vegetables', 'type': 'product'},
            {'name': 'Fruits', 'type': 'product'},
            {'name': 'Dairy Products', 'type': 'product'},
            {'name': 'Spices & Seasonings', 'type': 'product'},
            {'name': 'Alcoholic Beverages', 'type': 'product'},
            {'name': 'Non-alcoholic Beverages', 'type': 'product'},
            {'name': 'Frozen Foods', 'type': 'product'},
            {'name': 'Bakery & Desserts', 'type': 'product'},
            {'name': 'Cleaning & Supplies', 'type': 'product'},
            {'name': 'Tableware', 'type': 'product'},
            {'name': 'Kitchen Equipment', 'type': 'product'},
            {'name': 'Bar Supplies', 'type': 'product'},
            # Services (Non-Inventory)
            {'name': 'Service Charge', 'type': 'service'},
            {'name': 'Event Hosting', 'type': 'service'},
            {'name': 'Catering Service', 'type': 'service'},
            {'name': 'Other', 'type': 'product'},
        ],
        'extra_accounts': [
            {'code': '4150', 'name': 'Food Revenue', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '4160', 'name': 'Beverage & Bar Revenue', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '5100', 'name': 'Food Cost', 'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
            {'code': '5200', 'name': 'Beverage Cost', 'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
            {'code': '6050', 'name': 'Linen & Laundry', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
            {'code': '6055', 'name': 'Music & Entertainment', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
        ],
    },
    'construction': {
        'name': 'Construction / Contractor',
        'icon': 'bi-building',
        'business_type': 'product',
        'desc': 'General contractors, sub-contractors, renovation, civil works.',
        'categories': [
            # Products (Inventory)
            {'name': 'Cement & Concrete', 'type': 'product'},
            {'name': 'Steel & Metal', 'type': 'product'},
            {'name': 'Timber & Wood', 'type': 'product'},
            {'name': 'Bricks & Blocks', 'type': 'product'},
            {'name': 'Sand & Gravel', 'type': 'product'},
            {'name': 'Plumbing Materials', 'type': 'product'},
            {'name': 'Electrical Materials', 'type': 'product'},
            {'name': 'Paint & Finishing', 'type': 'product'},
            {'name': 'Roofing Materials', 'type': 'product'},
            {'name': 'Glass & Windows', 'type': 'product'},
            {'name': 'Hardware & Fasteners', 'type': 'product'},
            {'name': 'Safety Equipment', 'type': 'product'},
            {'name': 'Heavy Equipment Parts', 'type': 'product'},
            {'name': 'Tools', 'type': 'product'},
            # Services (Non-Inventory)
            {'name': 'Labor Charge', 'type': 'service'},
            {'name': 'Installation Service', 'type': 'service'},
            {'name': 'Sub-contractor Service', 'type': 'service'},
            {'name': 'Design & Consultation', 'type': 'service'},
            {'name': 'Equipment Rental', 'type': 'service'},
            {'name': 'Other', 'type': 'product'},
        ],
        'extra_accounts': [
            {'code': '1350', 'name': 'Work-in-Progress', 'account_type': 'Asset', 'sub_type': 'Current Asset', 'normal_balance': 'debit'},
            {'code': '1550', 'name': 'Heavy Equipment', 'account_type': 'Asset', 'sub_type': 'Fixed Asset', 'normal_balance': 'debit'},
            {'code': '4150', 'name': 'Contract Revenue', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '5100', 'name': 'Direct Materials', 'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
            {'code': '5200', 'name': 'Direct Labour', 'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
            {'code': '5300', 'name': 'Sub-contractor Costs', 'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
            {'code': '6050', 'name': 'Equipment Rental', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
            {'code': '6055', 'name': 'Permits & Licenses', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
        ],
    },
    'services': {
        'name': 'Professional Services',
        'icon': 'bi-briefcase',
        'business_type': 'service',
        'desc': 'Consulting, IT services, freelancing, agencies, law firms.',
        'categories': [
            {'name': 'Consulting Fee', 'type': 'service'},
            {'name': 'Service Charge', 'type': 'service'},
            {'name': 'IT Support', 'type': 'service'},
            {'name': 'Legal Service', 'type': 'service'},
            {'name': 'Accounting Service', 'type': 'service'},
            {'name': 'Design Services', 'type': 'service'},
            {'name': 'Marketing Services', 'type': 'service'},
            {'name': 'Training & Coaching', 'type': 'service'},
            {'name': 'Project Management', 'type': 'service'},
            {'name': 'Commission Fee', 'type': 'service'},
            {'name': 'Advisory Fee', 'type': 'service'},
            {'name': 'Retainer Fee', 'type': 'service'},
            {'name': 'Other', 'type': 'service'},
        ],
        'extra_accounts': [
            {'code': '4150', 'name': 'Consulting Revenue', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '4160', 'name': 'Project Revenue', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '5100', 'name': 'Direct Project Costs', 'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
            {'code': '6050', 'name': 'Software & Subscriptions', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
            {'code': '6055', 'name': 'Professional Development', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
        ],
    },
    'manufacturing': {
        'name': 'Manufacturing / Production',
        'icon': 'bi-gear',
        'business_type': 'product',
        'desc': 'Factories, assembly, processing, production facilities.',
        'categories': [
            # Products (Inventory)
            {'name': 'Raw Materials', 'type': 'product'},
            {'name': 'Semi-finished Goods', 'type': 'product'},
            {'name': 'Finished Goods', 'type': 'product'},
            {'name': 'Packaging Materials', 'type': 'product'},
            {'name': 'Machine Parts & Spares', 'type': 'product'},
            {'name': 'Tools & Dies', 'type': 'product'},
            {'name': 'Chemicals & Solvents', 'type': 'product'},
            {'name': 'Safety Supplies', 'type': 'product'},
            {'name': 'Lubricants & Oils', 'type': 'product'},
            {'name': 'Electrical Components', 'type': 'product'},
            {'name': 'Quality Control Supplies', 'type': 'product'},
            # Services (Non-Inventory)
            {'name': 'Labor Charge', 'type': 'service'},
            {'name': 'Maintenance Service', 'type': 'service'},
            {'name': 'Calibration Service', 'type': 'service'},
            {'name': 'Other', 'type': 'product'},
        ],
        'extra_accounts': [
            {'code': '1350', 'name': 'Work-in-Progress', 'account_type': 'Asset', 'sub_type': 'Current Asset', 'normal_balance': 'debit'},
            {'code': '1360', 'name': 'Raw Materials Inventory', 'account_type': 'Asset', 'sub_type': 'Current Asset', 'normal_balance': 'debit'},
            {'code': '1550', 'name': 'Machinery & Equipment', 'account_type': 'Asset', 'sub_type': 'Fixed Asset', 'normal_balance': 'debit'},
            {'code': '5100', 'name': 'Direct Materials', 'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
            {'code': '5200', 'name': 'Direct Labour', 'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
            {'code': '5300', 'name': 'Manufacturing Overhead', 'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
            {'code': '6050', 'name': 'Machine Maintenance', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
        ],
    },
    'healthcare': {
        'name': 'Healthcare / Medical',
        'icon': 'bi-heart-pulse',
        'business_type': 'service',
        'desc': 'Clinics, pharmacies, dental offices, veterinary.',
        'categories': [
            {'name': 'Consultation Fee', 'type': 'service'},
            {'name': 'Medical Service', 'type': 'service'},
            {'name': 'Lab Test Fee', 'type': 'service'},
            {'name': 'Dental Service', 'type': 'service'},
            {'name': 'Surgical Service', 'type': 'service'},
            {'name': 'Physiotherapy Service', 'type': 'service'},
            {'name': 'Veterinary Service', 'type': 'service'},
            {'name': 'Nursing Service', 'type': 'service'},
            {'name': 'Diagnostic Fee', 'type': 'service'},
            {'name': 'Vaccination Fee', 'type': 'service'},
            {'name': 'Prescription Fee', 'type': 'service'},
            {'name': 'Other', 'type': 'service'},
        ],
        'extra_accounts': [
            {'code': '4150', 'name': 'Medical Services Revenue', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '4160', 'name': 'Pharmacy Sales Revenue', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '1550', 'name': 'Medical Equipment', 'account_type': 'Asset', 'sub_type': 'Fixed Asset', 'normal_balance': 'debit'},
            {'code': '5100', 'name': 'Medical Supplies Cost', 'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
            {'code': '6050', 'name': 'Lab & Test Expenses', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
        ],
    },
    'education': {
        'name': 'Education / Training',
        'icon': 'bi-mortarboard',
        'business_type': 'service',
        'desc': 'Schools, tutoring centres, training providers, e-learning.',
        'categories': [
            {'name': 'Course Fee', 'type': 'service'},
            {'name': 'Training Fee', 'type': 'service'},
            {'name': 'Workshop Fee', 'type': 'service'},
            {'name': 'Tutoring Service', 'type': 'service'},
            {'name': 'Registration Fee', 'type': 'service'},
            {'name': 'Examination Fee', 'type': 'service'},
            {'name': 'Certification Fee', 'type': 'service'},
            {'name': 'Seminar Fee', 'type': 'service'},
            {'name': 'Coaching Service', 'type': 'service'},
            {'name': 'Online Course Fee', 'type': 'service'},
            {'name': 'Other', 'type': 'service'},
        ],
        'extra_accounts': [
            {'code': '4150', 'name': 'Tuition Revenue', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '4160', 'name': 'Course Materials Revenue', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '6050', 'name': 'Teaching Materials', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
            {'code': '6055', 'name': 'Student Activities', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
        ],
    },
    'agriculture': {
        'name': 'Agriculture / Farming',
        'icon': 'bi-tree',
        'business_type': 'product',
        'desc': 'Farms, plantations, livestock, fishing, agriculture supply.',
        'categories': [
            # Products (Inventory)
            {'name': 'Seeds & Seedlings', 'type': 'product'},
            {'name': 'Fertilizers', 'type': 'product'},
            {'name': 'Pesticides & Herbicides', 'type': 'product'},
            {'name': 'Animal Feed', 'type': 'product'},
            {'name': 'Livestock', 'type': 'product'},
            {'name': 'Farm Equipment Parts', 'type': 'product'},
            {'name': 'Irrigation Supplies', 'type': 'product'},
            {'name': 'Packaging', 'type': 'product'},
            {'name': 'Harvested Produce', 'type': 'product'},
            {'name': 'Dairy Products', 'type': 'product'},
            # Services (Non-Inventory)
            {'name': 'Harvesting Service', 'type': 'service'},
            {'name': 'Veterinary Service', 'type': 'service'},
            {'name': 'Equipment Rental', 'type': 'service'},
            {'name': 'Other', 'type': 'product'},
        ],
        'extra_accounts': [
            {'code': '1350', 'name': 'Biological Assets', 'account_type': 'Asset', 'sub_type': 'Current Asset', 'normal_balance': 'debit'},
            {'code': '1550', 'name': 'Farm Equipment', 'account_type': 'Asset', 'sub_type': 'Fixed Asset', 'normal_balance': 'debit'},
            {'code': '4150', 'name': 'Crop Revenue', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '4160', 'name': 'Livestock Revenue', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '5100', 'name': 'Seed & Fertilizer Cost', 'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
            {'code': '5200', 'name': 'Feed & Livestock Cost', 'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
        ],
    },
    'automotive': {
        'name': 'Automotive / Workshop',
        'icon': 'bi-car-front',
        'business_type': 'product',
        'desc': 'Car dealers, workshops, auto parts, car wash, tire shops.',
        'categories': [
            # Products (Inventory)
            {'name': 'Spare Parts', 'type': 'product'},
            {'name': 'Engine Parts', 'type': 'product'},
            {'name': 'Tyres & Wheels', 'type': 'product'},
            {'name': 'Body Parts', 'type': 'product'},
            {'name': 'Lubricants & Fluids', 'type': 'product'},
            {'name': 'Batteries', 'type': 'product'},
            {'name': 'Electrical Parts', 'type': 'product'},
            {'name': 'Accessories', 'type': 'product'},
            {'name': 'Cleaning Products', 'type': 'product'},
            {'name': 'Tools & Equipment', 'type': 'product'},
            # Services (Non-Inventory)
            {'name': 'Workshop Service', 'type': 'service'},
            {'name': 'Labor Charge', 'type': 'service'},
            {'name': 'Inspection Service', 'type': 'service'},
            {'name': 'Car Wash Service', 'type': 'service'},
            {'name': 'Towing Service', 'type': 'service'},
            {'name': 'Other', 'type': 'product'},
        ],
        'extra_accounts': [
            {'code': '4150', 'name': 'Service & Repair Revenue', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '4160', 'name': 'Parts Sales Revenue', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '5100', 'name': 'Parts Cost', 'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
            {'code': '5200', 'name': 'Labour Cost', 'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
            {'code': '6050', 'name': 'Equipment Maintenance', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
        ],
    },
    'realestate': {
        'name': 'Real Estate / Property',
        'icon': 'bi-house-door',
        'business_type': 'service',
        'desc': 'Property management, real estate agencies, rentals.',
        'categories': [
            {'name': 'Property Rental', 'type': 'service'},
            {'name': 'Equipment Rental', 'type': 'service'},
            {'name': 'Vehicle Rental', 'type': 'service'},
            {'name': 'Brokerage Fee', 'type': 'service'},
            {'name': 'Property Management Fee', 'type': 'service'},
            {'name': 'Maintenance Service', 'type': 'service'},
            {'name': 'Agency Fee', 'type': 'service'},
            {'name': 'Valuation Service', 'type': 'service'},
            {'name': 'Leasing Fee', 'type': 'service'},
            {'name': 'Consulting Fee', 'type': 'service'},
            {'name': 'Other', 'type': 'service'},
        ],
        'extra_accounts': [
            {'code': '1550', 'name': 'Investment Properties', 'account_type': 'Asset', 'sub_type': 'Fixed Asset', 'normal_balance': 'debit'},
            {'code': '4150', 'name': 'Rental Income', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '4160', 'name': 'Commission Income', 'account_type': 'Revenue', 'sub_type': 'Income', 'normal_balance': 'credit'},
            {'code': '6050', 'name': 'Property Maintenance', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
            {'code': '6055', 'name': 'Property Management Fees', 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
        ],
    },
    'other': {
        'name': 'Other / General',
        'icon': 'bi-three-dots',
        'business_type': 'product',
        'desc': "Don't see your industry? Start with a general-purpose setup.",
        'categories': [
            # Products (Inventory)
            {'name': 'General Products', 'type': 'product'},
            {'name': 'Raw Materials', 'type': 'product'},
            {'name': 'Spare Parts', 'type': 'product'},
            {'name': 'Office Supplies', 'type': 'product'},
            # Services (Non-Inventory)
            {'name': 'General Services', 'type': 'service'},
            {'name': 'Consulting Fee', 'type': 'service'},
            {'name': 'Service Charge', 'type': 'service'},
            {'name': 'Miscellaneous', 'type': 'product'},
        ],
        'extra_accounts': [],
    },
}


# ─── SETUP WIZARD (INDUSTRY SELECTION) ────────────────────────────────
@setup_bp.route('/', methods=['GET'])
@login_required
def index():
    """Redirect to the right step based on current state."""
    settings = CompanySettings.query.filter_by(user_id=current_user.id).first()
    if not settings or not settings.is_setup_complete:
        return redirect(url_for('setup.choose_industry'))
    return redirect(url_for('setup.settings'))


@setup_bp.route('/choose-industry', methods=['GET', 'POST'])
@login_required
def choose_industry():
    """Step after registration: pick your business type & company info."""
    settings = CompanySettings.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        industry_key = request.form.get('industry', 'other')
        company_name = request.form.get('company_name', '').strip() or 'My Company'
        currency_symbol = request.form.get('currency_symbol', '$').strip() or '$'

        if not settings:
            settings = CompanySettings(user_id=current_user.id)
            db.session.add(settings)

        settings.company_name = company_name
        settings.currency_symbol = currency_symbol
        settings.industry = industry_key

        # Replace any existing industry categories with the chosen industry's categories
        industry = INDUSTRIES.get(industry_key, INDUSTRIES['other'])
        settings.business_type = industry.get('business_type', 'product')
        settings.is_setup_complete = True
        db.session.commit()

        _replace_industry_categories(industry['categories'])

        # Seed default chart of accounts for this user (if first time)
        _seed_default_and_ifrs_accounts_for_user(current_user.id)
        _seed_industry_accounts(industry.get('extra_accounts', []))

        flash(f'Business set up as "{industry["name"]}" — categories and accounts configured!', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('setup/choose_industry.html', industries=INDUSTRIES, settings=settings)


@setup_bp.route('/change-industry', methods=['GET', 'POST'])
@login_required
def change_industry():
    """Allow changing industry — replaces industry categories, keeps custom ones."""
    settings = CompanySettings.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        industry_key = request.form.get('industry', 'other')
        company_name = request.form.get('company_name', '').strip() or 'My Company'
        currency_symbol = request.form.get('currency_symbol', '$').strip() or '$'

        if not settings:
            settings = CompanySettings(user_id=current_user.id)
            db.session.add(settings)

        settings.company_name = company_name
        settings.currency_symbol = currency_symbol
        settings.industry = industry_key
        settings.is_setup_complete = True
        db.session.commit()

        industry = INDUSTRIES.get(industry_key, INDUSTRIES['other'])
        settings.business_type = industry.get('business_type', 'product')
        db.session.commit()
        _replace_industry_categories(industry['categories'])
        _seed_industry_accounts(industry.get('extra_accounts', []))

        flash(f'Business type changed to "{industry["name"]}" — categories updated automatically!', 'success')
        return redirect(url_for('setup.settings'))

    return render_template('setup/change_industry.html', industries=INDUSTRIES, settings=settings)


@setup_bp.route('/api/industry-categories/<key>')
@login_required
def api_industry_categories(key):
    """Return category list for a given industry (for live preview)."""
    industry = INDUSTRIES.get(key)
    if not industry:
        return jsonify({'error': 'Unknown industry'}), 404
    custom_cats = Category.query.filter_by(user_id=current_user.id, is_custom=True).order_by(Category.name).all()
    # Normalize category names for response
    cat_list = []
    for item in industry['categories']:
        if isinstance(item, dict):
            cat_list.append({'name': item['name'], 'type': item.get('type', 'product')})
        else:
            cat_list.append({'name': item, 'type': 'product'})
    return jsonify({
        'industry_name': industry['name'],
        'categories': cat_list,
        'custom_categories': [c.name for c in custom_cats],
    })


@setup_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Company settings page (accessible from sidebar)."""
    from datetime import date as _date

    company = CompanySettings.query.filter_by(user_id=current_user.id).first()
    if not company:
        company = CompanySettings(user_id=current_user.id)
        db.session.add(company)
        db.session.commit()

    if request.method == 'POST':
        form_section = request.form.get('_section', 'general')

        if form_section == 'general':
            company.company_name = request.form.get('company_name', '').strip() or 'My Company'
            company.currency_symbol = request.form.get('currency_symbol', '$').strip() or '$'
            company.tagline = request.form.get('tagline', '').strip()
            company.description = request.form.get('description', '').strip()
            company.registration_number = request.form.get('registration_number', '').strip()
            company.tax_id = request.form.get('tax_id', '').strip()
            fd = request.form.get('founded_date', '').strip()
            company.founded_date = _date.fromisoformat(fd) if fd else None

        elif form_section == 'contact':
            company.email = request.form.get('email', '').strip()
            company.phone = request.form.get('phone', '').strip()
            company.website = request.form.get('website', '').strip()
            company.fax = request.form.get('fax', '').strip()

        elif form_section == 'address':
            company.address_line1 = request.form.get('address_line1', '').strip()
            company.address_line2 = request.form.get('address_line2', '').strip()
            company.city = request.form.get('city', '').strip()
            company.state = request.form.get('state', '').strip()
            company.postal_code = request.form.get('postal_code', '').strip()
            company.country = request.form.get('country', '').strip()

        elif form_section == 'logo':
            logo_file = request.files.get('logo')
            if logo_file and logo_file.filename:
                # Validate file type
                allowed = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}
                ext = logo_file.filename.rsplit('.', 1)[-1].lower() if '.' in logo_file.filename else ''
                if ext not in allowed:
                    flash('Invalid file type. Use PNG, JPG, GIF, SVG, or WebP.', 'warning')
                    return redirect(url_for('setup.settings'))

                # Save to static/uploads/
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)

                # Remove old logo
                if company.logo:
                    old_path = os.path.join(current_app.root_path, 'static', company.logo)
                    if os.path.exists(old_path):
                        os.remove(old_path)

                filename = f'logo_{uuid.uuid4().hex[:8]}.{ext}'
                save_path = os.path.join(upload_dir, filename)
                logo_file.save(save_path)
                company.logo = f'uploads/{filename}'

            # Handle logo removal
            if request.form.get('remove_logo') == '1':
                if company.logo:
                    old_path = os.path.join(current_app.root_path, 'static', company.logo)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                    company.logo = ''

        db.session.commit()
        flash('Company settings updated.', 'success')
        return redirect(url_for('setup.settings'))

    industry_info = INDUSTRIES.get(company.industry, {})
    return render_template('setup/settings.html', company=company, industry_info=industry_info, industries=INDUSTRIES, firebase_sync_enabled=firebase_enabled())


@setup_bp.route('/cloud-backup', methods=['POST'])
@login_required
def cloud_backup():
    """Manual full backup to Firebase."""
    success, message = full_backup()
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('setup.settings'))


@setup_bp.route('/cloud-restore', methods=['POST'])
@login_required
def cloud_restore():
    """Restore all data from Firebase to local SQLite."""
    success, message = full_restore()
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('setup.settings'))


# ─── HELPER FUNCTIONS ──────────────────────────────────────────────────
def _seed_industry_categories(category_names):
    """Add industry categories that don't already exist (initial setup).
    category_names can be strings or dicts with {name, type}."""
    existing = {c.name.lower() for c in Category.query.filter_by(user_id=current_user.id).all()}
    order = Category.query.filter_by(user_id=current_user.id).count()
    for item in category_names:
        if isinstance(item, dict):
            name = item['name']
            cat_type = item.get('type', 'product')
        else:
            name = item
            cat_type = 'product'
        if name.lower() not in existing:
            order += 1
            db.session.add(Category(name=name, category_type=cat_type, is_custom=False, sort_order=order, user_id=current_user.id))
    db.session.commit()


def _replace_industry_categories(new_category_names):
    """Remove old industry categories and seed new ones. Keep custom (user-created) categories.
    new_category_names can be strings or dicts with {name, type}."""
    # Nullify category_id on products pointing to industry categories being removed
    industry_cats = Category.query.filter_by(user_id=current_user.id, is_custom=False).all()
    industry_cat_ids = [c.id for c in industry_cats]
    if industry_cat_ids:
        Product.query.filter(Product.user_id == current_user.id, Product.category_id.in_(industry_cat_ids)).update(
            {Product.category_id: None}, synchronize_session='fetch'
        )
        # Delete old industry categories
        Category.query.filter(Category.user_id == current_user.id, Category.id.in_(industry_cat_ids)).delete(synchronize_session='fetch')
    db.session.flush()

    # Seed new industry categories
    existing_custom = {c.name.lower() for c in Category.query.filter_by(user_id=current_user.id, is_custom=True).all()}
    order = Category.query.filter_by(user_id=current_user.id).count()
    for item in new_category_names:
        if isinstance(item, dict):
            name = item['name']
            cat_type = item.get('type', 'product')
        else:
            name = item
            cat_type = 'product'
        if name.lower() not in existing_custom:
            order += 1
            db.session.add(Category(name=name, category_type=cat_type, is_custom=False, sort_order=order, user_id=current_user.id))
    db.session.commit()


def _seed_industry_accounts(extra_accounts):
    """Add industry-specific accounts that don't already exist."""
    existing_codes = {a.code for a in Account.query.filter_by(user_id=current_user.id).all()}
    for acct in extra_accounts:
        if acct['code'] not in existing_codes:
            db.session.add(Account(
                code=acct['code'],
                name=acct['name'],
                account_type=acct['account_type'],
                sub_type=acct.get('sub_type', ''),
                normal_balance=acct.get('normal_balance', 'debit'),
                is_system=True,
                user_id=current_user.id,
            ))
    db.session.commit()
