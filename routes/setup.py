from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from database.models import (db, CompanySettings, Category, Account, Product, log_activity,
                              Customer, Vendor, Invoice, InvoiceItem, Bill, BillItem,
                              PaymentReceived, PaymentMade, Expense,
                              JournalEntry, JournalLine, StockMovement,
                              CreditNote, CreditNoteItem, DebitNote, DebitNoteItem,
                              Budget, FiscalPeriod)
from database.firebase_sync import full_backup, full_restore, is_enabled as firebase_enabled
import os, uuid, io, json, zipfile
from datetime import datetime, date
from decimal import Decimal


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

        log_activity('create', 'CompanySettings', settings.id if settings else None,
                     settings.company_name if settings else company_name,
                     f'Initial business setup: industry={industry["name"]}, currency={currency_symbol}')
        db.session.commit()

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

        log_activity('update', 'CompanySettings', settings.id if settings else None,
                     settings.company_name,
                     f'Industry changed to "{industry["name"]}"')
        db.session.commit()

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
        log_activity('update', 'CompanySettings', company.id,
                     company.company_name,
                     f'Company settings updated (section: {form_section})')
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
    log_activity('backup', 'System', None, 'Cloud Backup',
                 f'Cloud backup {"completed successfully" if success else "failed"}: {message}')
    db.session.commit()
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('setup.settings'))


@setup_bp.route('/cloud-restore', methods=['POST'])
@login_required
def cloud_restore():
    """Restore all data from Firebase to local SQLite."""
    success, message = full_restore()
    log_activity('restore', 'System', None, 'Cloud Restore',
                 f'Cloud restore {"completed successfully" if success else "failed"}: {message}')
    db.session.commit()
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('setup.settings'))


# ─── DATA RESTORE FROM ZIP BACKUP ─────────────────────────────────────
@setup_bp.route('/restore', methods=['GET'])
@login_required
def restore_data_page():
    """Show the Data Restore page."""
    return render_template('setup/restore.html')


@setup_bp.route('/restore', methods=['POST'])
@login_required
def restore_data_upload():
    """Handle ZIP upload and restore user data."""
    from database.models import (
        Account, Customer, Vendor, Product as ProductModel, Category as CategoryModel,
        CompanySettings as CompanySettingsModel,
        Invoice, InvoiceItem, Bill, BillItem,
        PaymentReceived, PaymentMade, Expense,
        JournalEntry, JournalLine, StockMovement,
        CreditNote, CreditNoteItem, DebitNote, DebitNoteItem,
        Budget, FiscalPeriod
    )

    file = request.files.get('backup_file')
    if not file or not file.filename.endswith('.zip'):
        flash('Please upload a valid .zip backup file.', 'danger')
        return redirect(url_for('setup.restore_data_page'))

    restore_mode = request.form.get('restore_mode', 'merge')  # merge or replace

    try:
        zip_bytes = io.BytesIO(file.read())
        with zipfile.ZipFile(zip_bytes, 'r') as zf:
            # Validate: must contain backup_meta.json
            if 'backup_meta.json' not in zf.namelist():
                flash('Invalid backup file — missing backup_meta.json.', 'danger')
                return redirect(url_for('setup.restore_data_page'))

            meta = json.loads(zf.read('backup_meta.json'))

            # Read all data files
            def read_json(name):
                path = f'data/{name}.json'
                if path in zf.namelist():
                    return json.loads(zf.read(path))
                return []

            # ── If replace mode, wipe existing data ──
            if restore_mode == 'replace':
                uid = current_user.id
                # Delete child records first
                inv_ids = [i.id for i in Invoice.query.filter_by(user_id=uid).all()]
                if inv_ids:
                    InvoiceItem.query.filter(InvoiceItem.invoice_id.in_(inv_ids)).delete(synchronize_session=False)
                bill_ids = [b.id for b in Bill.query.filter_by(user_id=uid).all()]
                if bill_ids:
                    BillItem.query.filter(BillItem.bill_id.in_(bill_ids)).delete(synchronize_session=False)
                cn_ids = [c.id for c in CreditNote.query.filter_by(user_id=uid).all()]
                if cn_ids:
                    CreditNoteItem.query.filter(CreditNoteItem.credit_note_id.in_(cn_ids)).delete(synchronize_session=False)
                dn_ids = [d.id for d in DebitNote.query.filter_by(user_id=uid).all()]
                if dn_ids:
                    DebitNoteItem.query.filter(DebitNoteItem.debit_note_id.in_(dn_ids)).delete(synchronize_session=False)
                je_ids = [j.id for j in JournalEntry.query.filter_by(user_id=uid).all()]
                if je_ids:
                    JournalLine.query.filter(JournalLine.journal_entry_id.in_(je_ids)).delete(synchronize_session=False)
                # Delete main records
                PaymentReceived.query.filter_by(user_id=uid).delete(synchronize_session=False)
                PaymentMade.query.filter_by(user_id=uid).delete(synchronize_session=False)
                Invoice.query.filter_by(user_id=uid).delete(synchronize_session=False)
                Bill.query.filter_by(user_id=uid).delete(synchronize_session=False)
                CreditNote.query.filter_by(user_id=uid).delete(synchronize_session=False)
                DebitNote.query.filter_by(user_id=uid).delete(synchronize_session=False)
                Expense.query.filter_by(user_id=uid).delete(synchronize_session=False)
                JournalEntry.query.filter_by(user_id=uid).delete(synchronize_session=False)
                StockMovement.query.filter_by(user_id=uid).delete(synchronize_session=False)
                ProductModel.query.filter_by(user_id=uid).delete(synchronize_session=False)
                CategoryModel.query.filter_by(user_id=uid).delete(synchronize_session=False)
                Customer.query.filter_by(user_id=uid).delete(synchronize_session=False)
                Vendor.query.filter_by(user_id=uid).delete(synchronize_session=False)
                Account.query.filter_by(user_id=uid).delete(synchronize_session=False)
                Budget.query.filter_by(user_id=uid).delete(synchronize_session=False)
                FiscalPeriod.query.filter_by(user_id=uid).delete(synchronize_session=False)
                CompanySettingsModel.query.filter_by(user_id=uid).delete(synchronize_session=False)
                db.session.flush()

            # ── ID mapping: old backup IDs → new DB IDs ──
            id_map = {}  # { 'table_name': { old_id: new_id } }
            total_imported = 0
            uid = current_user.id

            def parse_date(val):
                if not val:
                    return None
                try:
                    return datetime.fromisoformat(val).date() if 'T' not in str(val) else datetime.fromisoformat(val).date()
                except (ValueError, TypeError):
                    try:
                        return datetime.strptime(str(val), '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        return None

            def parse_datetime(val):
                if not val:
                    return None
                try:
                    return datetime.fromisoformat(val)
                except (ValueError, TypeError):
                    return None

            def parse_decimal(val):
                if val is None:
                    return Decimal('0')
                try:
                    return Decimal(str(val))
                except Exception:
                    return Decimal('0')

            def parse_bool(val):
                if val is None:
                    return False
                if isinstance(val, bool):
                    return val
                return str(val).lower() in ('true', '1', 'yes')

            # ── Import master data ──
            # Company Settings
            cs_rows = read_json('company_settings')
            for row in cs_rows:
                cs = CompanySettingsModel(
                    user_id=uid,
                    company_name=row.get('company_name', 'My Company'),
                    industry=row.get('industry', ''),
                    business_type=row.get('business_type', 'product'),
                    currency_symbol=row.get('currency_symbol', '$'),
                    is_setup_complete=parse_bool(row.get('is_setup_complete', True)),
                    tagline=row.get('tagline', ''),
                    description=row.get('description', ''),
                    registration_number=row.get('registration_number', ''),
                    tax_id=row.get('tax_id', ''),
                    founded_date=parse_date(row.get('founded_date')),
                    logo=row.get('logo', ''),
                    email=row.get('email', ''),
                    phone=row.get('phone', ''),
                    website=row.get('website', ''),
                    fax=row.get('fax', ''),
                    address_line1=row.get('address_line1', ''),
                    address_line2=row.get('address_line2', ''),
                    city=row.get('city', ''),
                    state=row.get('state', ''),
                    postal_code=row.get('postal_code', ''),
                    country=row.get('country', ''),
                )
                db.session.add(cs)
                total_imported += 1

            # Categories
            id_map['categories'] = {}
            for row in read_json('categories'):
                old_id = row.get('id')
                cat = CategoryModel(
                    user_id=uid,
                    name=row.get('name', ''),
                    description=row.get('description', ''),
                    category_type=row.get('category_type', 'product'),
                    is_active=parse_bool(row.get('is_active', True)),
                    is_custom=parse_bool(row.get('is_custom', False)),
                    sort_order=row.get('sort_order', 0),
                )
                db.session.add(cat)
                db.session.flush()
                if old_id:
                    id_map['categories'][old_id] = cat.id
                total_imported += 1

            # Accounts
            id_map['accounts'] = {}
            for row in read_json('accounts'):
                old_id = row.get('id')
                acct = Account(
                    user_id=uid,
                    code=row.get('code', ''),
                    name=row.get('name', ''),
                    account_type=row.get('account_type', ''),
                    sub_type=row.get('sub_type', ''),
                    description=row.get('description', ''),
                    is_active=parse_bool(row.get('is_active', True)),
                    is_system=parse_bool(row.get('is_system', False)),
                    normal_balance=row.get('normal_balance', 'debit'),
                )
                db.session.add(acct)
                db.session.flush()
                if old_id:
                    id_map['accounts'][old_id] = acct.id
                total_imported += 1

            # Customers
            id_map['customers'] = {}
            for row in read_json('customers'):
                old_id = row.get('id')
                c = Customer(
                    user_id=uid,
                    name=row.get('name', ''),
                    email=row.get('email', ''),
                    phone=row.get('phone', ''),
                    address=row.get('address', ''),
                    city=row.get('city', ''),
                    tax_id=row.get('tax_id', ''),
                    credit_limit=parse_decimal(row.get('credit_limit')),
                    balance=parse_decimal(row.get('balance')),
                    is_active=parse_bool(row.get('is_active', True)),
                    notes=row.get('notes', ''),
                )
                db.session.add(c)
                db.session.flush()
                if old_id:
                    id_map['customers'][old_id] = c.id
                total_imported += 1

            # Vendors
            id_map['vendors'] = {}
            for row in read_json('vendors'):
                old_id = row.get('id')
                v = Vendor(
                    user_id=uid,
                    name=row.get('name', ''),
                    email=row.get('email', ''),
                    phone=row.get('phone', ''),
                    address=row.get('address', ''),
                    city=row.get('city', ''),
                    tax_id=row.get('tax_id', ''),
                    balance=parse_decimal(row.get('balance')),
                    is_active=parse_bool(row.get('is_active', True)),
                    notes=row.get('notes', ''),
                )
                db.session.add(v)
                db.session.flush()
                if old_id:
                    id_map['vendors'][old_id] = v.id
                total_imported += 1

            # Products
            id_map['products'] = {}
            for row in read_json('products'):
                old_id = row.get('id')
                p = ProductModel(
                    user_id=uid,
                    sku=row.get('sku', ''),
                    name=row.get('name', ''),
                    description=row.get('description', ''),
                    category=row.get('category', ''),
                    category_id=id_map['categories'].get(row.get('category_id')),
                    unit=row.get('unit', 'pcs'),
                    cost_price=parse_decimal(row.get('cost_price')),
                    selling_price=parse_decimal(row.get('selling_price')),
                    quantity_on_hand=parse_decimal(row.get('quantity_on_hand')),
                    reorder_level=parse_decimal(row.get('reorder_level')),
                    is_active=parse_bool(row.get('is_active', True)),
                    is_service=parse_bool(row.get('is_service', False)),
                    item_type=row.get('item_type', 'product'),
                    sub_category=row.get('sub_category', ''),
                    revenue_type=row.get('revenue_type', ''),
                    cost_behavior=row.get('cost_behavior', ''),
                    tax_type=row.get('tax_type', 'taxable'),
                    income_account_id=id_map['accounts'].get(row.get('income_account_id')),
                    expense_account_id=id_map['accounts'].get(row.get('expense_account_id')),
                    asset_account_id=id_map['accounts'].get(row.get('asset_account_id')),
                )
                db.session.add(p)
                db.session.flush()
                if old_id:
                    id_map['products'][old_id] = p.id
                total_imported += 1

            # ── Import transaction data ──
            # Journal Entries + Lines
            id_map['journal_entries'] = {}
            for row in read_json('journal_entries'):
                old_id = row.get('id')
                je = JournalEntry(
                    user_id=uid,
                    entry_number=row.get('entry_number', ''),
                    date=parse_date(row.get('date')) or date.today(),
                    description=row.get('description', ''),
                    reference=row.get('reference', ''),
                    source=row.get('source', ''),
                    is_posted=parse_bool(row.get('is_posted', False)),
                    is_adjusting=parse_bool(row.get('is_adjusting', False)),
                )
                db.session.add(je)
                db.session.flush()
                if old_id:
                    id_map['journal_entries'][old_id] = je.id
                total_imported += 1

            for row in read_json('journal_lines'):
                jl = JournalLine(
                    user_id=uid,
                    journal_entry_id=id_map['journal_entries'].get(row.get('journal_entry_id'), row.get('journal_entry_id')),
                    account_id=id_map['accounts'].get(row.get('account_id'), row.get('account_id')),
                    description=row.get('description', ''),
                    debit=parse_decimal(row.get('debit')),
                    credit=parse_decimal(row.get('credit')),
                )
                db.session.add(jl)
                total_imported += 1

            # Invoices + Items
            id_map['invoices'] = {}
            for row in read_json('invoices'):
                old_id = row.get('id')
                inv = Invoice(
                    user_id=uid,
                    invoice_number=row.get('invoice_number', ''),
                    customer_id=id_map['customers'].get(row.get('customer_id'), row.get('customer_id')),
                    date=parse_date(row.get('date')) or date.today(),
                    due_date=parse_date(row.get('due_date')),
                    status=row.get('status', 'draft'),
                    payment_type=row.get('payment_type', 'owe'),
                    subtotal=parse_decimal(row.get('subtotal')),
                    tax_rate=parse_decimal(row.get('tax_rate')),
                    tax_amount=parse_decimal(row.get('tax_amount')),
                    discount_amount=parse_decimal(row.get('discount_amount')),
                    total=parse_decimal(row.get('total')),
                    amount_paid=parse_decimal(row.get('amount_paid')),
                    balance_due=parse_decimal(row.get('balance_due')),
                    paid_date=parse_date(row.get('paid_date')),
                    notes=row.get('notes', ''),
                    journal_entry_id=id_map['journal_entries'].get(row.get('journal_entry_id')),
                )
                db.session.add(inv)
                db.session.flush()
                if old_id:
                    id_map['invoices'][old_id] = inv.id
                total_imported += 1

            for row in read_json('invoice_items'):
                ii = InvoiceItem(
                    invoice_id=id_map['invoices'].get(row.get('invoice_id'), row.get('invoice_id')),
                    product_id=id_map['products'].get(row.get('product_id')),
                    description=row.get('description', ''),
                    quantity=parse_decimal(row.get('quantity')),
                    unit_price=parse_decimal(row.get('unit_price')),
                    amount=parse_decimal(row.get('amount')),
                )
                db.session.add(ii)
                total_imported += 1

            # Bills + Items
            id_map['bills'] = {}
            for row in read_json('bills'):
                old_id = row.get('id')
                b = Bill(
                    user_id=uid,
                    bill_number=row.get('bill_number', ''),
                    vendor_id=id_map['vendors'].get(row.get('vendor_id'), row.get('vendor_id')),
                    date=parse_date(row.get('date')) or date.today(),
                    due_date=parse_date(row.get('due_date')),
                    payment_type=row.get('payment_type', 'owe'),
                    status=row.get('status', 'draft'),
                    subtotal=parse_decimal(row.get('subtotal')),
                    tax_rate=parse_decimal(row.get('tax_rate')),
                    tax_amount=parse_decimal(row.get('tax_amount')),
                    total=parse_decimal(row.get('total')),
                    amount_paid=parse_decimal(row.get('amount_paid')),
                    balance_due=parse_decimal(row.get('balance_due')),
                    notes=row.get('notes', ''),
                    journal_entry_id=id_map['journal_entries'].get(row.get('journal_entry_id')),
                    paid_date=parse_date(row.get('paid_date')),
                )
                db.session.add(b)
                db.session.flush()
                if old_id:
                    id_map['bills'][old_id] = b.id
                total_imported += 1

            for row in read_json('bill_items'):
                bi = BillItem(
                    bill_id=id_map['bills'].get(row.get('bill_id'), row.get('bill_id')),
                    product_id=id_map['products'].get(row.get('product_id')),
                    description=row.get('description', ''),
                    quantity=parse_decimal(row.get('quantity')),
                    unit_cost=parse_decimal(row.get('unit_cost')),
                    amount=parse_decimal(row.get('amount')),
                )
                db.session.add(bi)
                total_imported += 1

            # Payments Received
            for row in read_json('payments_received'):
                pr = PaymentReceived(
                    user_id=uid,
                    payment_number=row.get('payment_number', ''),
                    customer_id=id_map['customers'].get(row.get('customer_id'), row.get('customer_id')),
                    invoice_id=id_map['invoices'].get(row.get('invoice_id')),
                    date=parse_date(row.get('date')) or date.today(),
                    amount=parse_decimal(row.get('amount')),
                    payment_method=row.get('payment_method', ''),
                    reference=row.get('reference', ''),
                    deposit_to_account_id=id_map['accounts'].get(row.get('deposit_to_account_id')),
                    journal_entry_id=id_map['journal_entries'].get(row.get('journal_entry_id')),
                    notes=row.get('notes', ''),
                )
                db.session.add(pr)
                total_imported += 1

            # Payments Made
            for row in read_json('payments_made'):
                pm = PaymentMade(
                    user_id=uid,
                    payment_number=row.get('payment_number', ''),
                    vendor_id=id_map['vendors'].get(row.get('vendor_id'), row.get('vendor_id')),
                    bill_id=id_map['bills'].get(row.get('bill_id')),
                    date=parse_date(row.get('date')) or date.today(),
                    amount=parse_decimal(row.get('amount')),
                    payment_method=row.get('payment_method', ''),
                    reference=row.get('reference', ''),
                    paid_from_account_id=id_map['accounts'].get(row.get('paid_from_account_id')),
                    journal_entry_id=id_map['journal_entries'].get(row.get('journal_entry_id')),
                    notes=row.get('notes', ''),
                )
                db.session.add(pm)
                total_imported += 1

            # Expenses
            for row in read_json('expenses'):
                exp = Expense(
                    user_id=uid,
                    expense_number=row.get('expense_number', ''),
                    date=parse_date(row.get('date')) or date.today(),
                    category=row.get('category', ''),
                    vendor_id=id_map['vendors'].get(row.get('vendor_id')),
                    expense_account_id=id_map['accounts'].get(row.get('expense_account_id'), row.get('expense_account_id')),
                    paid_from_account_id=id_map['accounts'].get(row.get('paid_from_account_id'), row.get('paid_from_account_id')),
                    amount=parse_decimal(row.get('amount')),
                    payment_method=row.get('payment_method', ''),
                    reference=row.get('reference', ''),
                    description=row.get('description', ''),
                    journal_entry_id=id_map['journal_entries'].get(row.get('journal_entry_id')),
                )
                db.session.add(exp)
                total_imported += 1

            # Stock Movements
            for row in read_json('stock_movements'):
                sm = StockMovement(
                    user_id=uid,
                    product_id=id_map['products'].get(row.get('product_id'), row.get('product_id')),
                    date=parse_date(row.get('date')) or date.today(),
                    movement_type=row.get('movement_type', 'in'),
                    quantity=parse_decimal(row.get('quantity')),
                    unit_cost=parse_decimal(row.get('unit_cost')),
                    reference=row.get('reference', ''),
                    notes=row.get('notes', ''),
                )
                db.session.add(sm)
                total_imported += 1

            # Credit Notes + Items
            id_map['credit_notes'] = {}
            for row in read_json('credit_notes'):
                old_id = row.get('id')
                cn = CreditNote(
                    user_id=uid,
                    credit_note_number=row.get('credit_note_number', ''),
                    invoice_id=id_map['invoices'].get(row.get('invoice_id')),
                    customer_id=id_map['customers'].get(row.get('customer_id'), row.get('customer_id')),
                    date=parse_date(row.get('date')) or date.today(),
                    reason=row.get('reason', ''),
                    subtotal=parse_decimal(row.get('subtotal')),
                    tax_amount=parse_decimal(row.get('tax_amount')),
                    total=parse_decimal(row.get('total')),
                    status=row.get('status', 'draft'),
                    journal_entry_id=id_map['journal_entries'].get(row.get('journal_entry_id')),
                )
                db.session.add(cn)
                db.session.flush()
                if old_id:
                    id_map['credit_notes'][old_id] = cn.id
                total_imported += 1

            for row in read_json('credit_note_items'):
                cni = CreditNoteItem(
                    credit_note_id=id_map['credit_notes'].get(row.get('credit_note_id'), row.get('credit_note_id')),
                    product_id=id_map['products'].get(row.get('product_id')),
                    description=row.get('description', ''),
                    quantity=parse_decimal(row.get('quantity')),
                    unit_price=parse_decimal(row.get('unit_price')),
                    amount=parse_decimal(row.get('amount')),
                )
                db.session.add(cni)
                total_imported += 1

            # Debit Notes + Items
            id_map['debit_notes'] = {}
            for row in read_json('debit_notes'):
                old_id = row.get('id')
                dn = DebitNote(
                    user_id=uid,
                    debit_note_number=row.get('debit_note_number', ''),
                    bill_id=id_map['bills'].get(row.get('bill_id')),
                    vendor_id=id_map['vendors'].get(row.get('vendor_id'), row.get('vendor_id')),
                    date=parse_date(row.get('date')) or date.today(),
                    reason=row.get('reason', ''),
                    subtotal=parse_decimal(row.get('subtotal')),
                    tax_amount=parse_decimal(row.get('tax_amount')),
                    total=parse_decimal(row.get('total')),
                    status=row.get('status', 'draft'),
                    journal_entry_id=id_map['journal_entries'].get(row.get('journal_entry_id')),
                )
                db.session.add(dn)
                db.session.flush()
                if old_id:
                    id_map['debit_notes'][old_id] = dn.id
                total_imported += 1

            for row in read_json('debit_note_items'):
                dni = DebitNoteItem(
                    debit_note_id=id_map['debit_notes'].get(row.get('debit_note_id'), row.get('debit_note_id')),
                    product_id=id_map['products'].get(row.get('product_id')),
                    description=row.get('description', ''),
                    quantity=parse_decimal(row.get('quantity')),
                    unit_price=parse_decimal(row.get('unit_price')),
                    amount=parse_decimal(row.get('amount')),
                )
                db.session.add(dni)
                total_imported += 1

            # Budgets (unique constraint on account_id + year + month)
            for row in read_json('budgets'):
                acct_id = id_map['accounts'].get(row.get('account_id'), row.get('account_id'))
                b_year = row.get('year', 2025)
                b_month = row.get('month', 0)
                existing_budget = Budget.query.filter_by(
                    account_id=acct_id, year=b_year, month=b_month
                ).first()
                if existing_budget:
                    # Update existing budget instead of inserting duplicate
                    existing_budget.amount = parse_decimal(row.get('amount'))
                    existing_budget.notes = row.get('notes', '') or existing_budget.notes
                else:
                    bg = Budget(
                        user_id=uid,
                        account_id=acct_id,
                        year=b_year,
                        month=b_month,
                        amount=parse_decimal(row.get('amount')),
                        notes=row.get('notes', ''),
                    )
                    db.session.add(bg)
                total_imported += 1

            # Fiscal Periods (unique constraint on year + month)
            for row in read_json('fiscal_periods'):
                fp_year = row.get('year', 2025)
                fp_month = row.get('month', 1)
                existing_fp = FiscalPeriod.query.filter_by(
                    year=fp_year, month=fp_month
                ).first()
                if existing_fp:
                    # Update existing period instead of inserting duplicate
                    if parse_bool(row.get('is_locked', False)):
                        existing_fp.is_locked = True
                    if row.get('notes'):
                        existing_fp.notes = row.get('notes', '')
                else:
                    fp = FiscalPeriod(
                        user_id=uid,
                        year=fp_year,
                        month=fp_month,
                        is_locked=parse_bool(row.get('is_locked', False)),
                        notes=row.get('notes', ''),
                    )
                    db.session.add(fp)
                total_imported += 1

            db.session.commit()

        log_activity('restore', 'Backup', None, 'Data Restore',
                     f'Restored {total_imported} records from backup (mode: {restore_mode})')
        db.session.commit()
        flash(f'Data restored successfully! {total_imported} records imported.', 'success')

    except zipfile.BadZipFile:
        flash('The uploaded file is not a valid ZIP archive.', 'danger')
    except json.JSONDecodeError:
        flash('The backup contains invalid JSON data.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Restore failed: {str(e)}', 'danger')

    return redirect(url_for('setup.restore_data_page'))


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
