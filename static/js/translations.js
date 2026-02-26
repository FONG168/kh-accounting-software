/**
 * KH Accounting Software — Multi-language Translation Engine
 * Supports: English (en), Khmer (km)
 *
 * How it works:
 *   1. Language preference stored in localStorage('kh-lang')
 *   2. On page load, all text nodes are scanned and translated
 *   3. A MutationObserver watches for dynamic DOM changes
 *   4. Brand names (KH, KH., Accounting Software, Enterprise) are preserved
 */

const KH_TRANSLATIONS = {
    // ─── SIDEBAR NAVIGATION ────────────────────────────────────
    'Dashboard': 'ផ្ទាំងគ្រប់គ្រង',
    'SALES': 'ការលក់',
    'Customers': 'អតិថិជន',
    'Invoices / Sales': 'វិក្កយបត្រ / ការលក់',
    'Payments Received': 'ការទទួលប្រាក់',
    'PURCHASES': 'ការទិញ',
    'Vendors': 'អ្នកផ្គត់ផ្គង់',
    'Bills / Purchases': 'វិក្កយបត្រ / ការទិញ',
    'Payments Made': 'ការបង់ប្រាក់',
    'SERVICES': 'សេវាកម្ម',
    'INVENTORY': 'សារពើភ័ណ្ឌ',
    'Services': 'សេវាកម្ម',
    'Products & Services': 'ផលិតផល និង សេវាកម្ម',
    'Categories': 'ប្រភេទ',
    'Stock Movements': 'ចលនាស្តុក',
    'PETTY CASH': 'សាច់ប្រាក់រន្ធត់',
    'Petty Cash': 'សាច់ប្រាក់រន្ធត់',
    'ACCOUNTING': 'គណនេយ្យ',
    'Chart of Accounts': 'គម្រោងគណនី',
    'Journal Entries': 'បញ្ជីកំណត់ត្រា',
    'Credit Notes': 'កំណត់ត្រាឥណទាន',
    'Debit Notes': 'កំណត់ត្រាឥណពន្ធ',
    'REPORTS': 'របាយការណ៍',
    'Profit & Loss': 'ចំណេញ និង ខាត',
    'Balance Sheet': 'តារាងតុល្យការ',
    'Trial Balance': 'តុល្យភាពសាកល្បង',
    'Cash Flow': 'លំហូរសាច់ប្រាក់',
    'Changes in Equity': 'ការផ្លាស់ប្តូរមូលធន',
    'General Ledger': 'បញ្ជីគណនីទូទៅ',
    'Sales Report': 'របាយការណ៍ការលក់',
    'Expense Report': 'របាយការណ៍ចំណាយ',
    'Inventory Report': 'របាយការណ៍សារពើភ័ណ្ឌ',
    'Budget vs Actual': 'ថវិកា និង ជាក់ស្តែង',
    'AR Aging': 'អាយុកាលគណនីទទួល',
    'AP Aging': 'អាយុកាលគណនីបង់',
    'Customer Statement': 'របាយការណ៍អតិថិជន',
    'Vendor Statement': 'របាយការណ៍អ្នកផ្គត់ផ្គង់',
    'SETTINGS': 'ការកំណត់',
    'Company Settings': 'ការកំណត់ក្រុមហ៊ុន',
    'Fiscal Periods': 'រយៈពេលសារពើពន្ធ',
    'Budgets': 'ថវិកា',
    'Audit Log': 'កំណត់ត្រាសវនកម្ម',
    'Restore Data': 'ស្ដារទិន្នន័យ',
    'SUPPORT': 'ជំនួយ',
    'Live Chat Support': 'ជំនួយផ្ទាល់',

    // ─── TOP NAVBAR ────────────────────────────────────────────
    'Search…': 'ស្វែងរក…',
    'Cloud Sync': 'ធ្វើសមកាលកម្មពពក',
    'Local': 'មូលដ្ឋាន',
    'Signed in as': 'ចូលជា',
    'Settings': 'ការកំណត់',
    'Logout': 'ចេញ',

    // ─── COMMAND PALETTE ───────────────────────────────────────
    'Search customers, invoices, products, or type a command…': 'ស្វែងរកអតិថិជន វិក្កយបត្រ ផលិតផល ឬវាយពាក្យបញ្ជា…',
    'New Invoice': 'វិក្កយបត្រថ្មី',
    'New Bill': 'វិក្កយបត្រទិញថ្មី',
    'New Petty Cash': 'សាច់ប្រាក់រន្ធត់ថ្មី',
    'New Journal Entry': 'បញ្ជីកំណត់ត្រាថ្មី',
    'Page': 'ទំព័រ',
    'Action': 'សកម្មភាព',
    'Report': 'របាយការណ៍',

    // ─── AUTH PAGES ────────────────────────────────────────────
    'Welcome back': 'សូមស្វាគមន៍មកវិញ',
    'Sign in to your KH Accounting Software Enterprise account.': 'ចូលគណនី KH Accounting Software Enterprise របស់អ្នក។',
    'Email Address': 'អាសយដ្ឋានអ៊ីមែល',
    'Password': 'ពាក្យសម្ងាត់',
    'Enter your password': 'បញ្ចូលពាក្យសម្ងាត់របស់អ្នក',
    'Remember me': 'ចងចាំខ្ញុំ',
    'Sign In': 'ចូល',
    "Don't have an account?": 'មិនមានគណនី?',
    'Create one': 'បង្កើតគណនី',
    'Create your account': 'បង្កើតគណនីរបស់អ្នក',
    'Start managing your business finances in minutes.': 'ចាប់ផ្តើមគ្រប់គ្រងហិរញ្ញវត្ថុអាជីវកម្មរបស់អ្នកក្នុងរយៈពេលប៉ុន្មាននាទី។',
    'Full Name': 'ឈ្មោះពេញ',
    'Your full name': 'ឈ្មោះពេញរបស់អ្នក',
    'you@example.com': 'you@example.com',
    'Min 8 characters': 'យ៉ាងហោចណាស់ ៨ តួអក្សរ',
    'Confirm Password': 'បញ្ជាក់ពាក្យសម្ងាត់',
    'Re-enter password': 'បញ្ចូលពាក្យសម្ងាត់ម្តងទៀត',
    'Create Account': 'បង្កើតគណនី',
    'Already have an account?': 'មានគណនីរួចហើយ?',
    'Sign in': 'ចូល',

    // Auth - Recovery
    'Welcome Back!': 'សូមស្វាគមន៍មកវិញ!',
    'We found a previous account linked to this email.': 'យើងបានរកឃើញគណនីមុនដែលភ្ជាប់ជាមួយអ៊ីមែលនេះ។',
    'Previous account found!': 'រកឃើញគណនីមុន!',
    'The admin has allowed you to recover your previous data.': 'អ្នកគ្រប់គ្រងបានអនុញ្ញាតឱ្យអ្នកយកទិន្នន័យមុនរបស់អ្នកមកវិញ។',
    'New Password': 'ពាក្យសម្ងាត់ថ្មី',
    'What would you like to do?': 'តើអ្នកចង់ធ្វើអ្វី?',
    'Recover My Previous Data': 'យកទិន្នន័យមុនរបស់ខ្ញុំមកវិញ',
    'Start Completely Fresh': 'ចាប់ផ្តើមថ្មីទាំងស្រុង',
    'Restore your old account with all your invoices, expenses, journals, customers, and other data intact. Pick up right where you left off.': 'ស្ដារគណនីចាស់របស់អ្នកជាមួយវិក្កយបត្រ ចំណាយ បញ្ជី អតិថិជន និងទិន្នន័យផ្សេងទៀត។ បន្តពីកន្លែងដែលអ្នកបានឈប់។',
    'Delete all previous data and begin with a clean slate. Your old records will be permanently removed.': 'លុបទិន្នន័យទាំងអស់ពីមុន ហើយចាប់ផ្តើមថ្មី។ កំណត់ត្រាចាស់របស់អ្នកនឹងត្រូវបានលុបជាអចិន្ត្រៃយ៍។',
    'Select an option above': 'ជ្រើសរើសជម្រើសខាងលើ',
    'Recover My Account': 'យកគណនីរបស់ខ្ញុំមកវិញ',
    'Start Fresh': 'ចាប់ផ្តើមថ្មី',
    'Changed your mind?': 'ប្តូរចិត្តវិញ?',
    'Use a different email': 'ប្រើអ៊ីមែលផ្សេង',

    // Auth Branding
    'Professional accounting software': 'កម្មវិធីគណនេយ្យវិជ្ជាជីវៈ',
    'for every type of business': 'សម្រាប់គ្រប់ប្រភេទអាជីវកម្ម',
    'Professional accounting software<br>for every type of business': 'កម្មវិធីគណនេយ្យវិជ្ជាជីវៈ<br>សម្រាប់គ្រប់ប្រភេទអាជីវកម្ម',
    'Double-entry bookkeeping': 'បញ្ជីគណនេយ្យទ្វេ',
    'Sales, purchases & inventory': 'ការលក់ ការទិញ និង សារពើភ័ណ្ឌ',
    'Industry-specific categories': 'ប្រភេទឧស្សាហកម្មជាក់លាក់',
    'Profit & loss, balance sheet, cash flow': 'ចំណេញ និង ខាត តារាងតុល្យការ លំហូរសាច់ប្រាក់',
    'Multi-industry support': 'គាំទ្រឧស្សាហកម្មច្រើន',
    'Secure': 'សុវត្ថិភាព',
    'Fast': 'រហ័ស',
    'About This Software': 'អំពីកម្មវិធីនេះ',

    // ─── DASHBOARD ─────────────────────────────────────────────
    'Revenue': 'ចំណូល',
    'Expenses': 'ចំណាយ',
    'Receivables': 'គណនីទទួល',
    'Cash & Bank': 'សាច់ប្រាក់ និង ធនាគារ',
    'Revenue vs Expenses': 'ចំណូល ទល់នឹង ចំណាយ',
    'Net Profit': 'ចំណេញសុទ្ធ',
    'Net Income (MTD)': 'ចំណូលសុទ្ធ (ខែនេះ)',
    'Cash Breakdown': 'ការបែងចែកសាច់ប្រាក់',
    'Cash on Hand': 'សាច់ប្រាក់នៅក្នុងដៃ',
    'Bank Account': 'គណនីធនាគារ',
    'Total Liquid': 'សាច់ប្រាក់សរុប',
    'Payables': 'គណនីបង់',
    'Expense Breakdown': 'ការបែងចែកចំណាយ',
    'Financial Health': 'សុខភាពហិរញ្ញវត្ថុ',
    'Current Ratio': 'អនុបាតបច្ចុប្បន្ន',
    'Quick Ratio': 'អនុបាតរហ័ស',
    'Working Capital': 'ដើមទុនធ្វើការ',
    'Profit Margin': 'ចំណេញ',
    'profit margin': 'ចំណេញ',
    'Products': 'ផលិតផល',
    'Quick Actions': 'សកម្មភាពរហ័ស',
    'Invoice': 'វិក្កយបត្រ',
    'Bill': 'វិក្កយបត្រទិញ',
    'Expense': 'ចំណាយ',
    'Receive Payment': 'ទទួលប្រាក់',
    'Pay Bill': 'បង់វិក្កយបត្រ',
    'Journal': 'បញ្ជី',
    'P&L': 'ច&ខ',
    'Recent Invoices': 'វិក្កយបត្រថ្មីៗ',
    'View All': 'មើលទាំងអស់',
    'Customer': 'អតិថិជន',
    'Status': 'ស្ថានភាព',
    'Total': 'សរុប',
    'No invoices yet': 'មិនទាន់មានវិក្កយបត្រ',
    'Recent Bills': 'វិក្កយបត្រទិញថ្មីៗ',
    'Vendor': 'អ្នកផ្គត់ផ្គង់',
    'No bills yet': 'មិនទាន់មានវិក្កយបត្រទិញ',
    'Top Customers': 'អតិថិជនល្អបំផុត',
    'All Customers': 'អតិថិជនទាំងអស់',
    'Recent Petty Cash': 'សាច់ប្រាក់រន្ធត់ថ្មីៗ',
    'Category': 'ប្រភេទ',
    'Amount': 'ចំនួនទឹកប្រាក់',
    'No expenses yet': 'មិនទាន់មានចំណាយ',
    'Low Stock': 'ស្តុកទាប',
    'Product': 'ផលិតផល',
    'On Hand': 'នៅក្នុងដៃ',
    'Reorder': 'បញ្ជាទិញម្តងទៀត',
    'Bills Due Soon': 'វិក្កយបត្រផុតកំណត់ឆាប់ៗ',
    'Due': 'ផុតកំណត់',
    'View': 'មើល',

    // Dashboard KPI Modals
    'Expenses This Month': 'ចំណាយខែនេះ',
    'Bills': 'វិក្កយបត្រទិញ',
    'Total Due': 'សរុបត្រូវបង់',
    'Outstanding Receivables': 'គណនីទទួលមិនទាន់បង់',
    'Invoices': 'វិក្កយបត្រ',
    'Cash & Bank Transactions': 'ប្រតិបត្តិការសាច់ប្រាក់ និង ធនាគារ',
    'Money In': 'ប្រាក់ចូល',
    'Money Out': 'ប្រាក់ចេញ',
    'Balance': 'សមតុល្យ',
    'Payment #': 'លេខការបង់ប្រាក់',
    'Method': 'វិធីសាស្រ្ត',
    'No payments received yet': 'មិនទាន់មានការទទួលប្រាក់',
    'No payments made yet': 'មិនទាន់មានការបង់ប្រាក់',
    'No petty cash expenses yet': 'មិនទាន់មានចំណាយសាច់ប្រាក់រន្ធត់',
    'No expenses this month': 'មិនមានចំណាយក្នុងខែនេះ',
    'No outstanding receivables': 'គ្មានគណនីទទួលមិនទាន់បង់',

    // ─── ACCOUNTS ──────────────────────────────────────────────
    'New Account': 'គណនីថ្មី',
    'Asset': 'ទ្រព្យសកម្ម',
    'Liability': 'បំណុល',
    'Equity': 'មូលធន',
    'Code': 'លេខកូដ',
    'Account Name': 'ឈ្មោះគណនី',
    'Sub-Type': 'ប្រភេទរង',
    'Actions': 'សកម្មភាព',
    'System': 'ប្រព័ន្ធ',
    'Edit Account': 'កែគណនី',
    'Account Code *': 'លេខកូដគណនី *',
    'Account Name *': 'ឈ្មោះគណនី *',
    'Account Type *': 'ប្រភេទគណនី *',
    'Select Type': 'ជ្រើសរើសប្រភេទ',
    'None': 'គ្មាន',
    'Current Asset': 'ទ្រព្យសកម្មបច្ចុប្បន្ន',
    'Fixed Asset': 'ទ្រព្យសកម្មថេរ',
    'Other Asset': 'ទ្រព្យសកម្មផ្សេង',
    'Current Liability': 'បំណុលបច្ចុប្បន្ន',
    'Long-term Liability': 'បំណុលរយៈពេលវែង',
    'Owner Equity': 'មូលធនម្ចាស់',
    'Retained Earnings': 'ចំណេញរក្សាទុក',
    'Operating Revenue': 'ចំណូលប្រតិបត្តិការ',
    'Other Revenue': 'ចំណូលផ្សេង',
    'Cost of Goods Sold': 'តម្លៃទំនិញលក់',
    'Operating Expense': 'ចំណាយប្រតិបត្តិការ',
    'Other Expense': 'ចំណាយផ្សេង',
    'Parent Account': 'គណនីមេ',
    'None (Top Level)': 'គ្មាន (កម្រិតកំពូល)',
    'Description': 'ការពណ៌នា',
    'Update Account': 'ធ្វើបច្ចុប្បន្នភាពគណនី',
    'Create Account': 'បង្កើតគណនី',
    'Cancel': 'បោះបង់',
    'Delete': 'លុប',
    'Edit': 'កែ',

    // ─── CUSTOMERS ─────────────────────────────────────────────
    'New Customer': 'អតិថិជនថ្មី',
    'Search': 'ស្វែងរក',
    'Name, email or phone…': 'ឈ្មោះ អ៊ីមែល ឬទូរស័ព្ទ…',
    'City': 'ទីក្រុង',
    'All Cities': 'ទីក្រុងទាំងអស់',
    'Has Balance': 'មានសមតុល្យ',
    'Zero Balance': 'សមតុល្យសូន្យ',
    'Active': 'សកម្ម',
    'Inactive': 'អសកម្ម',
    'Filter': 'តម្រង',
    'Clear': 'សម្អាត',
    'Name': 'ឈ្មោះ',
    'Email': 'អ៊ីមែល',
    'Phone': 'ទូរស័ព្ទ',
    'No customers found.': 'រកមិនឃើញអតិថិជន។',
    'Tax ID': 'លេខពន្ធ',
    'Address': 'អាសយដ្ឋាន',
    'Credit Limit': 'កំណត់ឥណទាន',
    'Notes': 'កំណត់ចំណាំ',
    'Update': 'ធ្វើបច្ចុប្បន្នភាព',
    'Create': 'បង្កើត',

    // ─── VENDORS ───────────────────────────────────────────────
    'Vendors / Suppliers': 'អ្នកផ្គត់ផ្គង់',
    'New Vendor': 'អ្នកផ្គត់ផ្គង់ថ្មី',
    'No vendors found.': 'រកមិនឃើញអ្នកផ្គត់ផ្គង់។',

    // ─── SALES ─────────────────────────────────────────────────
    'All Customers': 'អតិថិជនទាំងអស់',
    'Paid': 'បានបង់',
    'Owed': 'ជំពាក់',
    'Partial': 'មួយផ្នែក',
    'Overdue': 'ផុតកំណត់',
    'Draft': 'សេចក្តីព្រាង',
    'From': 'ពី',
    'Invoice #': 'វិក្កយបត្រ #',
    'Date': 'កាលបរិច្ឆេទ',
    'Due Date': 'កាលបរិច្ឆេទផុតកំណត់',
    'Balance Due': 'សមតុល្យត្រូវបង់',
    'PAID': 'បានបង់',
    'OWED': 'ជំពាក់',
    'OVERDUE': 'ផុតកំណត់',
    'PARTIAL': 'មួយផ្នែក',
    'DRAFT': 'សេចក្តីព្រាង',
    'No invoices found.': 'រកមិនឃើញវិក្កយបត្រ។',
    'Receive payment': 'ទទួលការបង់ប្រាក់',

    // ─── PURCHASES ─────────────────────────────────────────────
    'All Vendors': 'អ្នកផ្គត់ផ្គង់ទាំងអស់',
    'Bill #': 'វិក្កយបត្រទិញ #',
    'No bills found.': 'រកមិនឃើញវិក្កយបត្រទិញ។',
    'Pay this bill': 'បង់វិក្កយបត្រនេះ',
    'Pay Now': 'បង់ឥឡូវ',
    'Total owed:': 'សរុបជំពាក់:',

    // ─── INVENTORY ─────────────────────────────────────────────
    'Stock History': 'ប្រវត្តិស្តុក',
    'Adjustment': 'ការកែតម្រូវ',
    'New Product': 'ផលិតផលថ្មី',
    'New Service': 'សេវាកម្មថ្មី',
    'SKU': 'SKU',
    'Type': 'ប្រភេទ',
    'Service': 'សេវាកម្ម',
    'Cost Price': 'តម្លៃដើម',
    'Selling Price': 'តម្លៃលក់',
    'Qty on Hand': 'បរិមាណនៅក្នុងដៃ',
    'Reorder Level': 'កម្រិតបញ្ជាទិញម្តងទៀត',

    // ─── EXPENSES ──────────────────────────────────────────────
    'Petty Cash Expenses': 'ចំណាយសាច់ប្រាក់រន្ធត់',
    'New Petty Cash Expense': 'ចំណាយសាច់ប្រាក់រន្ធត់ថ្មី',
    'Petty Cash Balance': 'សមតុល្យសាច់ប្រាក់រន្ធត់',
    'Total Expenses': 'ចំណាយសរុប',
    'Payment': 'ការបង់ប្រាក់',
    'Cash': 'សាច់ប្រាក់',
    'PC #': 'PC #',
    'Reference': 'ឯកសារយោង',
    'No petty cash expenses yet. Click New Petty Cash Expense to record one.': 'មិនទាន់មានចំណាយសាច់ប្រាក់រន្ធត់។ ចុច "ចំណាយសាច់ប្រាក់រន្ធត់ថ្មី" ដើម្បីកត់ត្រា។',

    // ─── JOURNAL ───────────────────────────────────────────────
    'New Entry': 'បញ្ជីថ្មី',
    'Entry #': 'បញ្ជី #',
    'Source': 'ប្រភព',
    'Debit': 'ឥណពន្ធ',
    'Credit': 'ឥណទាន',
    'Posted': 'បានផ្សាយ',
    'Create Reversing Entry': 'បង្កើតបញ្ជីបញ្ច្រាស',
    'No journal entries yet.': 'មិនទាន់មានបញ្ជីកំណត់ត្រា។',
    'Previous': 'មុន',
    'Next': 'បន្ទាប់',

    // ─── CREDIT NOTES ──────────────────────────────────────────
    'New Credit Note': 'កំណត់ត្រាឥណទានថ្មី',
    'CN #': 'CN #',
    'Reason': 'មូលហេតុ',
    'Applied': 'បានអនុវត្ត',
    'Void': 'ទុកជាមោឃៈ',
    'No credit notes found.': 'រកមិនឃើញកំណត់ត្រាឥណទាន។',

    // ─── DEBIT NOTES ───────────────────────────────────────────
    'New Debit Note': 'កំណត់ត្រាឥណពន្ធថ្មី',
    'DN #': 'DN #',
    'No debit notes found.': 'រកមិនឃើញកំណត់ត្រាឥណពន្ធ។',

    // ─── CATEGORIES ────────────────────────────────────────────
    'Product & Service Categories': 'ប្រភេទផលិតផល និង សេវាកម្ម',
    'New Category': 'ប្រភេទថ្មី',
    'Category Name': 'ឈ្មោះប្រភេទ',
    'Parent': 'មេ',
    'Custom': 'ផ្ទាល់ខ្លួន',
    'Industry': 'ឧស្សាហកម្ម',
    'No categories yet.': 'មិនទាន់មានប្រភេទ។',

    // ─── REPORTS ───────────────────────────────────────────────
    'Print': 'បោះពុម្ព',
    'PDF': 'PDF',
    'Apply': 'អនុវត្ត',
    'As of': 'គិតត្រឹម',
    'Year': 'ឆ្នាំ',

    // P&L
    'Profit & Loss Statement': 'របាយការណ៍ចំណេញ និង ខាត',
    'Current Period': 'រយៈពេលបច្ចុប្បន្ន',
    'Prior Period': 'រយៈពេលមុន',
    'No revenue recorded': 'មិនមានចំណូលកត់ត្រា',
    'Total Revenue': 'ចំណូលសរុប',
    'No cost of goods sold recorded': 'គ្មានតម្លៃទំនិញលក់បានកត់ត្រា',
    'Total COGS': 'តម្លៃទំនិញលក់សរុប',
    'Gross Profit': 'ចំណេញដុល',
    'Operating Expenses': 'ចំណាយប្រតិបត្តិការ',
    'No operating expenses recorded': 'គ្មានចំណាយប្រតិបត្តិការបានកត់ត្រា',
    'Total Operating Expenses': 'ចំណាយប្រតិបត្តិការសរុប',
    'Net Income': 'ចំណូលសុទ្ធ',
    'Net Loss': 'ខាតសុទ្ធ',

    // Balance Sheet
    'Assets': 'ទ្រព្យសកម្ម',
    'Total Assets': 'ទ្រព្យសកម្មសរុប',
    'Liabilities': 'បំណុល',
    'Total Liabilities': 'បំណុលសរុប',
    'Total Equity': 'មូលធនសរុប',
    'Total Liabilities & Equity': 'បំណុល និង មូលធនសរុប',

    // Trial Balance
    'Difference': 'ភាពខុសគ្នា',

    // Cash Flow
    'Cash Flow Statement': 'របាយការណ៍លំហូរសាច់ប្រាក់',
    'Cash Flow Statement (Indirect Method)': 'របាយការណ៍លំហូរសាច់ប្រាក់ (វិធីសាស្រ្តដោយប្រយោល)',
    '1. Cash Flow from Operating Activities': '១. លំហូរសាច់ប្រាក់ពីសកម្មភាពប្រតិបត្តិការ',
    '2. Cash Flow from Investing Activities': '២. លំហូរសាច់ប្រាក់ពីសកម្មភាពវិនិយោគ',
    '3. Cash Flow from Financing Activities': '៣. លំហូរសាច់ប្រាក់ពីសកម្មភាពហិរញ្ញប្បទាន',
    '4. Net Change in Cash': '៤. ការផ្លាស់ប្តូរសាច់ប្រាក់សរុប',
    'Net Cash from Operating Activities': 'សាច់ប្រាក់សុទ្ធពីប្រតិបត្តិការ',
    'Net Cash from Investing Activities': 'សាច់ប្រាក់សុទ្ធពីវិនិយោគ',
    'Net Cash from Financing Activities': 'សាច់ប្រាក់សុទ្ធពីហិរញ្ញប្បទាន',
    'Net Cash from Operating': 'សាច់ប្រាក់សុទ្ធពីប្រតិបត្តិការ',
    'Net Cash from Investing': 'សាច់ប្រាក់សុទ្ធពីវិនិយោគ',
    'Net Cash from Financing': 'សាច់ប្រាក់សុទ្ធពីហិរញ្ញប្បទាន',
    'Opening Cash Balance': 'សមតុល្យសាច់ប្រាក់ដើម',
    'Closing Cash Balance': 'សមតុល្យសាច់ប្រាក់ចុង',
    'No investing activity this period': 'គ្មានសកម្មភាពវិនិយោគក្នុងរយៈពេលនេះ',
    'No financing activity this period': 'គ្មានសកម្មភាពហិរញ្ញប្បទានក្នុងរយៈពេលនេះ',

    // Changes in Equity
    'Statement of Changes in Equity': 'របាយការណ៍ការផ្លាស់ប្តូរមូលធន',
    'Statement of Changes in Equity (IAS 1.106)': 'របាយការណ៍ការផ្លាស់ប្តូរមូលធន (IAS 1.106)',
    'Account': 'គណនី',
    'Opening Balance': 'សមតុល្យដើម',
    'Changes': 'ការផ្លាស់ប្តូរ',
    'Closing Balance': 'សមតុល្យចុង',
    'Net Income for the Period': 'ចំណូលសុទ្ធក្នុងរយៈពេល',

    // General Ledger
    '-- Select Account --': '-- ជ្រើសរើសគណនី --',
    'Select an account to view its general ledger.': 'ជ្រើសរើសគណនីដើម្បីមើលបញ្ជីគណនីទូទៅ។',

    // Sales Report
    'Total Sales': 'ការលក់សរុប',
    'Collected': 'បានប្រមូល',
    'Outstanding': 'មិនទាន់បង់',
    'Daily Sales Summary': 'សង្ខេបការលក់ប្រចាំថ្ងៃ',
    'Invoice Details': 'ព័ត៌មានលម្អិតវិក្កយបត្រ',
    'No sales in this period.': 'គ្មានការលក់ក្នុងរយៈពេលនេះ។',

    // Expense Report
    'All Categories': 'ប្រភេទទាំងអស់',
    'Expenses by Category': 'ចំណាយតាមប្រភេទ',
    'Count': 'ចំនួន',
    '% of Total': '% នៃសរុប',
    'Uncategorized': 'គ្មានប្រភេទ',
    'Expense Details': 'ព័ត៌មានលម្អិតចំណាយ',
    'Exp #': 'ចំណាយ #',
    'No expenses in this period.': 'គ្មានចំណាយក្នុងរយៈពេលនេះ។',

    // Inventory Report
    'Stock levels, movements & tracking': 'កម្រិតស្តុក ចលនា និង ការតាមដាន',
    'Inventory Value': 'តម្លៃសារពើភ័ណ្ឌ',
    'Stock In': 'ស្តុកចូល',
    'Stock Out': 'ស្តុកចេញ',
    'Adjustments': 'ការកែតម្រូវ',
    'Negative Stock Alert!': 'ការជូនដំណឹងស្តុកអវិជ្ជមាន!',
    'Low Stock': 'ស្តុកទាប',

    // Budget vs Actual
    'Budget vs Actual Report': 'របាយការណ៍ថវិកា ទល់នឹង ជាក់ស្តែង',
    'Budget': 'ថវិកា',
    'Actual': 'ជាក់ស្តែង',
    'Variance': 'គម្លាត',
    'Var %': 'គម្លាត %',

    // AR/AP Aging
    'Accounts Receivable Aging': 'អាយុកាលគណនីទទួល',
    'Accounts Payable Aging': 'អាយុកាលគណនីបង់',
    'Current': 'បច្ចុប្បន្ន',
    '31-60 Days': '៣១-៦០ ថ្ងៃ',
    '61-90 Days': '៦១-៩០ ថ្ងៃ',
    '90+ Days': '៩០+ ថ្ងៃ',
    'No outstanding receivables.': 'គ្មានគណនីទទួលមិនទាន់បង់។',
    'No outstanding payables.': 'គ្មានគណនីបង់មិនទាន់បង់។',

    // ─── FISCAL ────────────────────────────────────────────────
    'Fiscal Year': 'ឆ្នាំសារពើពន្ធ',
    'Year Start': 'ឆ្នាំចាប់ផ្តើម',
    'Year End': 'ឆ្នាំបញ្ចប់',
    'Period': 'រយៈពេល',
    'Start Date': 'កាលបរិច្ឆេទចាប់ផ្តើម',
    'End Date': 'កាលបរិច្ឆេទបញ្ចប់',
    'Closed': 'បានបិទ',
    'Open': 'បើក',
    'Close Period': 'បិទរយៈពេល',

    // ─── BUDGETS ───────────────────────────────────────────────
    'New Budget': 'ថវិកាថ្មី',
    'Budget Name': 'ឈ្មោះថវិកា',
    'Start': 'ចាប់ផ្តើម',
    'End Date': 'កាលបរិច្ឆេទបញ្ចប់',
    'Allocated': 'បានបែងចែក',
    'Spent': 'បានចំណាយ',
    'Remaining': 'នៅសល់',

    // ─── AUDIT LOG ─────────────────────────────────────────────
    'Audit Trail': 'កំណត់ត្រាសវនកម្ម',
    'Action': 'សកម្មភាព',
    'Entity': 'អង្គភាព',
    'User': 'អ្នកប្រើប្រាស់',
    'Details': 'ព័ត៌មានលម្អិត',
    'Timestamp': 'ពេលវេលា',

    // ─── SETUP / SETTINGS ──────────────────────────────────────
    'Choose Your Industry': 'ជ្រើសរើសឧស្សាហកម្មរបស់អ្នក',
    'Select the type of business that best describes your company.': 'ជ្រើសរើសប្រភេទអាជីវកម្មដែលពណ៌នាក្រុមហ៊ុនរបស់អ្នកបានល្អបំផុត។',
    'Company Name': 'ឈ្មោះក្រុមហ៊ុន',
    'Currency Symbol': 'និមិត្តសញ្ញារូបិយបណ្ណ',
    'Business Type': 'ប្រភេទអាជីវកម្ម',
    'Logo': 'ឡូហ្គោ',
    'Save Settings': 'រក្សាទុកការកំណត់',
    'Save': 'រក្សាទុក',

    // ─── ADMIN ─────────────────────────────────────────────────
    'Admin Panel': 'ផ្ទាំងគ្រប់គ្រងអ្នកគ្រប់គ្រង',
    'Users': 'អ្នកប្រើប្រាស់',
    'Pending Approvals': 'ការអនុម័តដែលកំពុងរង់ចាំ',
    'Announcements': 'សេចក្តីប្រកាស',
    'Backup': 'បម្រុងទុក',
    'Approve': 'អនុម័ត',
    'Reject': 'បដិសេធ',
    'Suspend': 'ផ្អាក',
    'Lock': 'ចាក់សោ',
    'Unlock': 'ដោះសោ',

    // ─── CHAT ──────────────────────────────────────────────────
    'Chat': 'ជជែក',
    'Send': 'ផ្ញើ',
    'Type a message...': 'វាយសារ...',

    // ─── ABOUT PAGE ────────────────────────────────────────────
    'Back to Sign In': 'ត្រលប់ទៅការចូល',
    'About KH Accounting Software': 'អំពី KH Accounting Software',
    'A professional, enterprise-grade accounting platform proudly built in Cambodia — designed for businesses of every size and industry.': 'វេទិកាគណនេយ្យវិជ្ជាជីវៈ ដែលបានបង្កើតនៅកម្ពុជា — ត្រូវបានរចនាសម្រាប់អាជីវកម្មគ្រប់ទំហំ និង ឧស្សាហកម្ម។',
    'The Creator': 'អ្នកបង្កើត',
    'Our Mission': 'បេសកកម្មរបស់យើង',
    'What Makes Us Special': 'អ្វីដែលធ្វើឱ្យយើងពិសេស',
    'Built in 2026': 'បង្កើតក្នុងឆ្នាំ ២០២៦',
    'Journal entries & audit trail': 'បញ្ជីកំណត់ត្រា និង កំណត់ត្រាសវនកម្ម',
    'Budget management': 'គ្រប់គ្រងថវិកា',
    'Cloud sync & secure data': 'ធ្វើសមកាលកម្មពពក និង សុវត្ថិភាពទិន្នន័យ',
    'Credit & debit notes': 'កំណត់ត្រាឥណទាន និង ឥណពន្ធ',
    'Multi-industry category support': 'គាំទ្រប្រភេទឧស្សាហកម្មច្រើន',

    // ─── COMMON / MISC ─────────────────────────────────────────
    'Loading...': 'កំពុងផ្ទុក...',
    'Error': 'កំហុស',
    'Success': 'ជោគជ័យ',
    'Warning': 'ការព្រមាន',
    'Info': 'ព័ត៌មាន',
    'Confirm': 'បញ្ជាក់',
    'Yes': 'បាទ/ចាស',
    'Close': 'បិទ',
    'Back': 'ត្រលប់',
    'Submit': 'ដាក់ស្នើ',
    'Download': 'ទាញយក',
    'Upload': 'ផ្ទុកឡើង',
    'Export': 'នាំចេញ',
    'Import': 'នាំចូល',
    'Showing': 'បង្ហាញ',
    'items': 'ធាតុ',
    'item': 'ធាតុ',
    'records': 'កំណត់ត្រា',
    'No data available': 'គ្មានទិន្នន័យ',
    'transaction': 'ប្រតិបត្តិការ',
    'transactions': 'ប្រតិបត្តិការ',
    'invoice': 'វិក្កយបត្រ',
    'invoices': 'វិក្កយបត្រ',
    'bill': 'វិក្កយបត្រទិញ',
    'bills': 'វិក្កយបត្រទិញ',
    'overdue': 'ផុតកំណត់',
    'MTD': 'ខែនេះ',
    'YTD': 'ឆ្នាំនេះ',
    '(MTD)': '(ខែនេះ)',
    '(YTD)': '(ឆ្នាំនេះ)',
    '(6 mo)': '(៦ ខែ)',
    'this month': 'ខែនេះ',
    'bills MTD': 'វិក្កយបត្រទិញខែនេះ',
    'received': 'បានទទួល',
    'issued': 'បានចេញ',
    'corrections': 'ការកែតម្រូវ',
    'due within 7 days': 'ផុតកំណត់ក្នុង ៧ ថ្ងៃ',
    'Today': 'ថ្ងៃនេះ',

    // ─── GREETINGS (Dashboard) ─────────────────────────────────
    'Good morning': 'អរុណសួស្តី',
    'Good afternoon': 'ទិវាសួស្តី',
    'Good evening': 'សាយ័ណសួស្តី',

    // ─── DAY NAMES ─────────────────────────────────────────────
    'Monday': 'ច័ន្ទ',
    'Tuesday': 'អង្គារ',
    'Wednesday': 'ពុធ',
    'Thursday': 'ព្រហស្បតិ៍',
    'Friday': 'សុក្រ',
    'Saturday': 'សៅរ៍',
    'Sunday': 'អាទិត្យ',

    // ─── MONTH NAMES ───────────────────────────────────────────
    'January': 'មករា',
    'February': 'កុម្ភៈ',
    'March': 'មីនា',
    'April': 'មេសា',
    'May': 'ឧសភា',
    'June': 'មិថុនា',
    'July': 'កក្កដា',
    'August': 'សីហា',
    'September': 'កញ្ញា',
    'October': 'តុលា',
    'November': 'វិច្ឆិកា',
    'December': 'ធ្នូ',

    // ─── SETUP INDUSTRY PAGE ───────────────────────────────────
    'Retail & General Trade': 'ការលក់រាយ និង ពាណិជ្ជកម្មទូទៅ',
    'Food & Beverage': 'អាហារ និង ភេសជ្ជៈ',
    'Construction': 'សំណង់',
    'Real Estate': 'អចលនទ្រព្យ',
    'Manufacturing': 'ផលិតកម្ម',
    'Technology': 'បច្ចេកវិទ្យា',
    'Healthcare': 'សុខាភិបាល',
    'Education': 'អប់រំ',
    'Agriculture': 'កសិកម្ម',
    'Transportation': 'ដឹកជញ្ជូន',
    'Hospitality': 'បដិសណ្ឋារកិច្ច',
    'Professional Services': 'សេវាកម្មវិជ្ជាជីវៈ',
    'Consulting': 'ប្រឹក្សាយោបល់',
    'Freelancer': 'អ្នកធ្វើការឯករាជ្យ',
    'Non-Profit': 'អង្គការមិនរកប្រាក់ចំណេញ',
    'Other': 'ផ្សេងៗ',

    // ── Language selector ──
    'Language': 'ភាសា',
    'English': 'English',
    'ខ្មែរ': 'ខ្មែរ',

    // ─── SETUP / SETTINGS PAGE ─────────────────────────────────
    'General': 'ទូទៅ',
    'Contact': 'ទំនាក់ទំនង',
    'Address': 'អាសយដ្ឋាន',
    'System': 'ប្រព័ន្ធ',
    'Company Profile': 'ប្រវត្តិក្រុមហ៊ុន',
    'Contact Information': 'ព័ត៌មានទំនាក់ទំនង',
    'Business Address': 'អាសយដ្ឋានអាជីវកម្ម',
    'Profile Preview': 'មើលប្រវត្តិជាមុន',
    'Company Logo': 'ឡូហ្គោក្រុមហ៊ុន',
    'Business Industry': 'ឧស្សាហកម្មអាជីវកម្ម',
    'Tagline / Motto': 'ពាក្យស្លោក / បាវចនា',
    'About the Company': 'អំពីក្រុមហ៊ុន',
    'Business Registration No.': 'លេខចុះបញ្ជីអាជីវកម្ម',
    'Date Founded': 'កាលបរិច្ឆេទបង្កើត',
    'Change Industry': 'ប្តូរឧស្សាហកម្ម',
    'Select Industry': 'ជ្រើសរើសឧស្សាហកម្ម',
    'Business Email': 'អ៊ីមែលអាជីវកម្ម',
    'Phone Number': 'លេខទូរស័ព្ទ',
    'Website': 'គេហទំព័រ',
    'Fax': 'ទូរសារ',
    'Upload Logo': 'ផ្ទុកឡើងឡូហ្គោ',
    'Address Line 1': 'អាសយដ្ឋានបន្ទាត់ ១',
    'Address Line 2': 'អាសយដ្ឋានបន្ទាត់ ២',
    'State / Province': 'រដ្ឋ / ខេត្ត',
    'Postal Code': 'លេខកូដប្រៃសណីយ៍',
    'Country': 'ប្រទេស',
    'Save Profile': 'រក្សាទុកប្រវត្តិ',
    'Save Contact Info': 'រក្សាទុកព័ត៌មានទំនាក់ទំនង',
    'Save Address': 'រក្សាទុកអាសយដ្ឋាន',
    'Remove': 'លុបចេញ',
    'Go to Categories': 'ទៅប្រភេទ',
    'Manage Categories': 'គ្រប់គ្រងប្រភេទ',
    'Restore from Cloud': 'ស្ដារពីពពក',
    'Full Backup': 'បម្រុងទុកពេញ',
    'No industry selected yet.': 'មិនទាន់បានជ្រើសរើសឧស្សាហកម្ម។',
    'Fill in your profile details to see a preview here.': 'បំពេញព័ត៌មានលម្អិតប្រវត្តិរបស់អ្នក ដើម្បីមើលការមើលជាមុន។',
    'Why add contact info?': 'ហេតុអ្វីត្រូវបន្ថែមព័ត៌មានទំនាក់ទំនង?',
    'Your business contact details will appear on invoices, bills, and printed reports — making your documents look professional and giving clients a way to reach you.': 'ព័ត៌មានទំនាក់ទំនងអាជីវកម្មរបស់អ្នកនឹងបង្ហាញនៅលើវិក្កយបត្រ វិក្កយបត្រទិញ និងរបាយការណ៍បោះពុម្ព — ធ្វើឱ្យឯកសាររបស់អ្នកមើលទៅវិជ្ជាជីវៈ និងផ្តល់ឱ្យអតិថិជននូវវិធីទាក់ទងអ្នក។',
    'Business address usage': 'ការប្រើប្រាស់អាសយដ្ឋានអាជីវកម្ម',
    'This address will appear on your invoices, bills, and official documents. Make sure it matches your registered business address for legal and tax purposes.': 'អាសយដ្ឋាននេះនឹងបង្ហាញនៅលើវិក្កយបត្រ វិក្កយបត្រទិញ និងឯកសារផ្លូវការ។ សូមប្រាកដថាវាត្រូវនឹងអាសយដ្ឋានអាជីវកម្មដែលបានចុះបញ្ជីសម្រាប់គោលបំណងច្បាប់ និងពន្ធ។',
    'Cloud Sync Active': 'ការធ្វើសមកាលកម្មពពកសកម្ម',
    'Every transaction is automatically saved to Firebase.': 'រាល់ប្រតិបត្តិការត្រូវបានរក្សាទុកដោយស្វ័យប្រវត្តិនៅ Firebase។',
    'Cloud Sync Disabled': 'ការធ្វើសមកាលកម្មពពកបិទ',
    'Cloud Sync (Firebase)': 'ធ្វើសមកាលកម្មពពក (Firebase)',
    'Data is stored locally only (SQLite).': 'ទិន្នន័យត្រូវបានរក្សាទុកក្នុងតំបន់តែប៉ុណ្ណោះ (SQLite)។',
    'How to enable:': 'របៀបបើក:',
    'Reg:': 'ចុះបញ្ជី:',
    'Founded:': 'បង្កើត:',
    'PNG, JPG, SVG or WebP. Max 2 MB recommended.': 'PNG, JPG, SVG ឬ WebP។ អនុសាសន៍អតិបរមា ២ MB។',
    'Remove the logo?': 'លុបឡូហ្គោ?',
    'e.g. Building dreams since 2010': 'ឧ. កសាងក្តីសុបិនចាប់ពីឆ្នាំ ២០១០',
    'Brief description of your business...': 'ការពណ៌នាសង្ខេបអំពីអាជីវកម្មរបស់អ្នក...',
    'e.g. SSM / EIN / ABN': 'ឧ. SSM / EIN / ABN',
    'e.g. GST / VAT / TIN number': 'ឧ. GST / VAT / TIN',
    'info@company.com': 'info@company.com',
    '+60 12-345 6789': '+60 12-345 6789',
    'https://www.company.com': 'https://www.company.com',
    'Optional': 'ជម្រើស',
    'Street address, P.O. box': 'អាសយដ្ឋានផ្លូវ, ប្រអប់សំបុត្រ',
    'Suite, unit, building, floor (optional)': 'បន្ទប់ អគារ ជាន់ (ជម្រើស)',
    'Add, edit, or remove product & service categories used across your system.': 'បន្ថែម កែ ឬលុបប្រភេទផលិតផល និងសេវាកម្មដែលប្រើក្នុងប្រព័ន្ធរបស់អ្នក។',

    // ─── SETUP / CHOOSE INDUSTRY ───────────────────────────────
    'Choose Your Business Type': 'ជ្រើសរើសប្រភេទអាជីវកម្មរបស់អ្នក',
    'Set up your business': 'រៀបចំអាជីវកម្មរបស់អ្នក',
    'Tell us about your business so we can configure the right categories, chart of accounts, and workflows for you.': 'ប្រាប់យើងអំពីអាជីវកម្មរបស់អ្នក ដើម្បីឱ្យយើងអាចកំណត់រចនាសម្ព័ន្ធប្រភេទ គម្រោងគណនី និងលំហូរការងារត្រឹមត្រូវសម្រាប់អ្នក។',
    'Register': 'ចុះឈ្មោះ',
    'Business Type': 'ប្រភេទអាជីវកម្ម',
    'Company / Business Name *': 'ឈ្មោះក្រុមហ៊ុន / អាជីវកម្ម *',
    'Currency': 'រូបិយប័ណ្ណ',
    'What type of business do you run?': 'តើអ្នកដំណើរការអាជីវកម្មប្រភេទណា?',
    'Service Business': 'អាជីវកម្មសេវាកម្ម',
    'Product Business': 'អាជីវកម្មផលិតផល',
    'Continue to Dashboard': 'បន្តទៅផ្ទាំងគ្រប់គ្រង',
    'Your business name': 'ឈ្មោះអាជីវកម្មរបស់អ្នក',

    // ─── SETUP / CHANGE INDUSTRY ───────────────────────────────
    'Change Business Type': 'ប្តូរប្រភេទអាជីវកម្ម',
    'Category Preview': 'មើលប្រភេទជាមុន',
    'Select New Business Type': 'ជ្រើសរើសប្រភេទអាជីវកម្មថ្មី',
    'New Industry Categories': 'ប្រភេទឧស្សាហកម្មថ្មី',
    'Your Custom Categories (kept)': 'ប្រភេទផ្ទាល់ខ្លួនរបស់អ្នក (រក្សាទុក)',
    'Back to Settings': 'ត្រលប់ទៅការកំណត់',
    'Old industry categories will be removed and replaced with the ones shown above.': 'ប្រភេទឧស្សាហកម្មចាស់នឹងត្រូវបានលុប ហើយជំនួសដោយប្រភេទដែលបង្ហាញខាងលើ។',

    // ─── SETUP / RESTORE ───────────────────────────────────────
    'Restore Data from Backup': 'ស្ដារទិន្នន័យពីការបម្រុងទុក',
    'How to Restore': 'របៀបស្ដារ',
    'Important Notes': 'ចំណាំសំខាន់',
    'Upload Backup File': 'ផ្ទុកឡើងឯកសារបម្រុងទុក',
    'Select Backup ZIP File': 'ជ្រើសរើសឯកសារ ZIP បម្រុងទុក',
    'Restore Mode': 'របៀបស្ដារ',
    'Merge': 'បញ្ចូលរួម',
    'Replace': 'ជំនួស',
    'Confirm & Restore': 'បញ្ជាក់ និង ស្ដារ',
    'Restore Data': 'ស្ដារទិន្នន័យ',
    'Click to select or drag & drop your ZIP file': 'ចុចជ្រើសរើស ឬអូសទម្លាក់ឯកសារ ZIP របស់អ្នក',
    'Only .zip files from admin backup are supported': 'គាំទ្រតែឯកសារ .zip ពីការបម្រុងទុកអ្នកគ្រប់គ្រង',
    'Add backup data to your existing records. No data will be deleted.': 'បន្ថែមទិន្នន័យបម្រុងទុកទៅកំណត់ត្រាដែលមានស្រាប់។ ទិន្នន័យនឹងមិនត្រូវបានលុបទេ។',
    'Delete all current data first, then import backup.': 'លុបទិន្នន័យបច្ចុប្បន្នទាំងអស់ជាមុន បន្ទាប់មកនាំចូលការបម្រុងទុក។',
    'Irreversible!': 'មិនអាចត្រឡប់វិញបាន!',
    'I understand this will import data into my account and confirm I want to proceed.': 'ខ្ញុំយល់ថាវានឹងនាំចូលទិន្នន័យទៅក្នុងគណនីរបស់ខ្ញុំ ហើយខ្ញុំបញ្ជាក់ថាខ្ញុំចង់បន្ត។',

    // ─── RESTORE PAGE — text fragments (split by <strong>/<code> tags) ──
    'Request your admin to export a backup of your data': 'ស្នើសុំអ្នកគ្រប់គ្រងរបស់អ្នកឲ្យនាំចេញការបំរុងទុកទិន្នៀយរបស់អ្នក',
    'The admin will send you a .zip file': 'អ្នកគ្រប់គ្រងនឹងផ្ញើអ្នកនូវឯកសារ .zip',
    'Upload the ZIP file using the form on the left': 'ផ្ទុកឡើងឯកសារ ZIP ដោយប្រើទំរង់នៅខាងឆ្វេង',
    'Choose': 'ជ្រើសរើស',
    '(add to existing) or': '(បន្ថែមទៅក្នុងទិន្នៀយដែលមានស្រាប់) ឬ',
    '(clean start)': '(ចាប់ផ្តើមឡើងវិញ)',
    'Click': 'ចុច',
    'and wait for import to complete': 'ហើយរង់ចាំដល់ការនាំចូលបញ្ចប់',
    'Merge mode': 'របៀបបញ្ចូលរួម',
    'is safe — it only adds new records alongside your existing data': 'មានសុវត្ថិភាព — វាបន្ថែមតែកំណត់ត្រាថ្មីស្រប់ជាមួយទិន្នៀយដែលមានស្រាប់របស់អ្នក',
    'Replace mode': 'របៀបជំនួស',
    'will permanently delete all your current data before importing — use with caution': 'នឹងលុបទិន្នៀយបច្ចុប្បន្នរបស់អ្នកស្ថាវរមុនពេលនាំចូល — ប្រើដោយប្រុប្រែង',
    'Only ZIP files generated by the admin backup feature are supported': 'គាំទ្រតែឯកសារ ZIP ដែលបង្កើតដោយមុខងារបំរុងទុករបស់អ្នកគ្រប់គ្រង',
    'The backup file must contain a': 'ឯកសារបំរុងទុកត្រូវតែមាន',
    'file to be valid': 'ឯកសារដើម្បី​មានសុពលភាព',
    'Large backups may take a few moments to import': 'ការបំរុងទុកធំអាចចំណាយពេលវេលាមួយចំនួនដើម្បីនាំចូល',
    'Remove': 'លុប',


    // ─── ADMIN PANEL ───────────────────────────────────────────
    'Admin Panel': 'ផ្ទាំងគ្រប់គ្រងអ្នកគ្រប់គ្រង',
    'System Admin': 'អ្នកគ្រប់គ្រងប្រព័ន្ធ',
    'Control Panel': 'ផ្ទាំងបញ្ជា',
    'Overview': 'ទិដ្ឋភាពទូទៅ',
    'User Management': 'គ្រប់គ្រងអ្នកប្រើប្រាស់',
    'Communications': 'ទំនាក់ទំនង',
    'Data Management': 'គ្រប់គ្រងទិន្នន័យ',
    'Backup & Recovery': 'បម្រុងទុក និង ស្ដារ',
    'System Owner': 'ម្ចាស់ប្រព័ន្ធ',
    'Super Admin': 'អ្នកគ្រប់គ្រងកំពូល',
    'Total Users': 'អ្នកប្រើប្រាស់សរុប',
    'Unread Chats': 'សារមិនបានអាន',
    'Pending': 'កំពុងរង់ចាំ',
    'Suspended': 'ផ្អាក',
    'Locked': 'ចាក់សោ',
    'System Health & Activity': 'សុខភាព និង សកម្មភាពប្រព័ន្ធ',
    'User Activity Overview': 'ទិដ្ឋភាពទូទៅសកម្មភាពអ្នកប្រើប្រាស់',
    'Per-User Breakdown': 'ការបែងចែកតាមអ្នកប្រើប្រាស់',
    'Recent Activity': 'សកម្មភាពថ្មីៗ',
    'New This Week': 'ថ្មីសប្តាហ៍នេះ',
    'Logins Today': 'ការចូលថ្ងៃនេះ',
    'Actions This Week': 'សកម្មភាពសប្តាហ៍នេះ',
    'Never Logged In': 'មិនទាន់បានចូល',
    'Registration Approval': 'ការអនុម័តការចុះឈ្មោះ',
    'Pending Registrations': 'ការចុះឈ្មោះកំពុងរង់ចាំ',
    'Manage Users': 'គ្រប់គ្រងអ្នកប្រើប្រាស់',
    'Review & approve new user signups': 'ពិនិត្យ និង អនុម័តការចុះឈ្មោះអ្នកប្រើប្រាស់ថ្មី',
    'View, suspend, lock, or remove accounts': 'មើល ផ្អាក ចាក់សោ ឬលុបគណនី',
    'Respond to user support messages': 'ឆ្លើយតបសាររបស់អ្នកប្រើប្រាស់',
    'Live': 'បើកដំណើរការ',
    'ON': 'បើក',
    'OFF': 'បិទ',
    'No users registered yet': 'មិនទាន់មានអ្នកប្រើប្រាស់ចុះឈ្មោះ',
    'No activity recorded yet': 'មិនទាន់មានសកម្មភាពកត់ត្រា',
    'Confirm Action': 'បញ្ជាក់សកម្មភាព',
    'Are you sure?': 'តើអ្នកប្រាកដទេ?',

    // Admin — Users
    'All Users': 'អ្នកប្រើប្រាស់ទាំងអស់',
    'Manage user accounts, roles, suspend, lock, or remove': 'គ្រប់គ្រងគណនី តួនាទី ផ្អាក ចាក់សោ ឬលុបអ្នកប្រើប្រាស់',
    'Approval': 'ការអនុម័ត',
    'Account Status': 'ស្ថានភាពគណនី',
    'Last Login': 'ការចូលចុងក្រោយ',
    'Registered': 'បានចុះឈ្មោះ',
    'Reactivate': 'បើកដំណើរការឡើងវិញ',
    'Set Role': 'កំណត់តួនាទី',
    'Viewer': 'អ្នកមើល',
    'Accountant': 'គណនេយ្យករ',
    'Admin': 'អ្នកគ្រប់គ្រង',
    'SUPERADMIN': 'អ្នកគ្រប់គ្រងកំពូល',
    'Approved': 'បានអនុម័ត',
    'Rejected': 'បានបដិសេធ',
    'Search by name or email...': 'ស្វែងរកតាមឈ្មោះ ឬអ៊ីមែល...',

    // Admin — Pending
    'Review and approve or reject new user registrations': 'ពិនិត្យ និង អនុម័ត ឬបដិសេធការចុះឈ្មោះអ្នកប្រើប្រាស់ថ្មី',
    'Registered On': 'ចុះឈ្មោះនៅ',
    'Approve Registration': 'អនុម័តការចុះឈ្មោះ',
    'Reject User': 'បដិសេធអ្នកប្រើប្រាស់',
    'Reason for rejection (optional)': 'មូលហេតុនៃការបដិសេធ (ជម្រើស)',
    'No Pending Registrations': 'គ្មានការចុះឈ្មោះកំពុងរង់ចាំ',
    'All user registrations have been processed.': 'ការចុះឈ្មោះអ្នកប្រើប្រាស់ទាំងអស់ត្រូវបានដំណើរការ។',
    'Explain why the registration is being rejected...': 'ពន្យល់ហេតុអ្វីការចុះឈ្មោះត្រូវបានបដិសេធ...',

    // Admin — Backup
    'Data Backup & Recovery': 'បម្រុងទុក និង ស្ដារទិន្នន័យ',
    'Export User Data': 'នាំចេញទិន្នន័យអ្នកប្រើប្រាស់',
    'Select User': 'ជ្រើសរើសអ្នកប្រើប្រាស់',
    'Date Range': 'ចន្លោះកាលបរិច្ឆេទ',
    'From Date': 'ពីកាលបរិច្ឆេទ',
    'To Date': 'ដល់កាលបរិច្ឆេទ',
    'Preview': 'មើលជាមុន',
    'Total Records': 'កំណត់ត្រាសរុប',
    '— Choose a user —': '— ជ្រើសរើសអ្នកប្រើប្រាស់ —',
    'Last 7 Days': '៧ ថ្ងៃចុងក្រោយ',
    'Last 30 Days': '៣០ ថ្ងៃចុងក្រោយ',
    'Last 90 Days': '៩០ ថ្ងៃចុងក្រោយ',
    'Last Year': 'ឆ្នាំមុន',
    'All Data': 'ទិន្នន័យទាំងអស់',
    'Download Backup': 'ទាញយកការបម្រុងទុក',
    'Download ZIP Backup': 'ទាញយកការបម្រុងទុក ZIP',
    'Select a user to see a preview': 'ជ្រើសរើសអ្នកប្រើប្រាស់ ដើម្បីមើលជាមុន',

    // Admin — Announcements
    'Broadcast messages to all users': 'ផ្សព្វផ្សាយសារទៅអ្នកប្រើប្រាស់ទាំងអស់',
    'New Announcement': 'សេចក្តីប្រកាសថ្មី',
    'Title': 'ចំណងជើង',
    'Message': 'សារ',
    'Expires (optional)': 'ផុតកំណត់ (ជម្រើស)',
    'Options': 'ជម្រើស',
    'Urgent': 'បន្ទាន់',
    'Pin to top': 'ខ្ទាស់នៅផ្នែកខាងលើ',
    'Publish Announcement': 'ផ្សាយសេចក្តីប្រកាស',
    'Deactivate': 'បិទដំណើរការ',
    'Activate': 'បើកដំណើរការ',
    'LIVE': 'កំពុងដំណើរការ',
    'Announcement title...': 'ចំណងជើងសេចក្តីប្រកាស...',
    'Write your announcement here...': 'សរសេរសេចក្តីប្រកាសរបស់អ្នកនៅទីនេះ...',

    // Admin — Chat
    'View and respond to user conversations': 'មើល និង ឆ្លើយតបការសន្ទនាអ្នកប្រើប្រាស់',
    'Back to Admin': 'ត្រលប់ទៅអ្នកគ្រប់គ្រង',
    'No Conversations Yet': 'មិនទាន់មានការសន្ទនា',
    'When users send messages, they will appear here.': 'នៅពេលអ្នកប្រើប្រាស់ផ្ញើសារ ពួកវានឹងបង្ហាញនៅទីនេះ។',
    'Manage User': 'គ្រប់គ្រងអ្នកប្រើប្រាស់',
    'No messages yet. Start the conversation.': 'មិនទាន់មានសារ។ ចាប់ផ្តើមការសន្ទនា។',

    // ─── SALES — FORMS & VIEWS ─────────────────────────────────
    'Line Items': 'បន្ទាត់ធាតុ',
    'Payment Option': 'ជម្រើសការបង់ប្រាក់',
    'Payment Method': 'វិធីបង់ប្រាក់',
    'Deposit To Account *': 'ដាក់បញ្ចូលទៅគណនី *',
    'Tax Rate %': 'អត្រាពន្ធ %',
    'Invoice (Pay Later)': 'វិក្កយបត្រ (បង់ពេលក្រោយ)',
    'Cash Sale (Pay Now)': 'ការលក់សាច់ប្រាក់ (បង់ឥឡូវ)',
    'Bank Transfer': 'ផ្ទេរធនាគារ',
    'Card': 'កាត',
    'Check': 'មូលប្បទានបត្រ',
    'E-Wallet': 'កាបូបអេឡិចត្រូនិច',
    'Add Line': 'បន្ថែមបន្ទាត់',
    'Product / Service': 'ផលិតផល / សេវាកម្ម',
    'Qty': 'បរិមាណ',
    'Unit Price': 'តម្លៃឯកតា',
    'Select Product': 'ជ្រើសរើសផលិតផល',
    'Select Service': 'ជ្រើសរើសសេវាកម្ម',
    'Select Customer': 'ជ្រើសរើសអតិថិជន',
    'Subtotal:': 'សរុបរួម:',
    'Tax:': 'ពន្ធ:',
    'Discount:': 'បញ្ចុះតម្លៃ:',
    'Total:': 'សរុប:',
    // ─── SALES PAGES (auto-added) ───
    'Invoice # or customer…': '\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A # \u17AC\u200B\u17A2\u178F\u17B7\u1790\u17B7\u1787\u1793\u2026',
    'Record Payment': '\u1780\u178F\u17CB\u178F\u17D2\u179A\u17B6\u1780\u17B6\u179A\u1794\u1784\u17CB\u1794\u17D2\u179A\u17B6\u1780\u17CB',
    'Record Payment Received': '\u1780\u178F\u17CB\u178F\u17D2\u179A\u17B6\u1780\u17B6\u179A\u1791\u1791\u17BD\u179B\u1794\u17D2\u179A\u17B6\u1780\u17CB',
    'Receiving payment for': '\u1791\u1791\u17BD\u179B\u1780\u17B6\u179A\u1794\u1784\u17CB\u1794\u17D2\u179A\u17B6\u1780\u17CB\u179F\u1798\u17D2\u179A\u17B6\u1794\u17CB',
    'No specific invoice': '\u1782\u17D2\u1798\u17B6\u1793\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A\u1787\u17B6\u1780\u17CB\u179B\u17B6\u1780\u17CB',
    'Customer pays later — record as owed': '\u17A2\u178F\u17B7\u1790\u17B7\u1787\u1793\u1794\u1784\u17CB\u1796\u17C1\u179B\u1780\u17D2\u179A\u17C4\u1799 \u2014 \u1780\u178F\u17CB\u178F\u17D2\u179A\u17B6\u1787\u17B6\u1787\u17C6\u1796\u17B6\u1780\u17CB',
    'Customer pays immediately — mark as paid': '\u17A2\u178F\u17B7\u1790\u17B7\u1787\u1793\u1794\u1784\u17CB\u1797\u17D2\u179B\u17B6\u1798 \u2014 \u179F\u1798\u17D2\u1782\u17B6\u179B\u17CB\u1790\u17B6\u1794\u17B6\u1793\u1794\u1784\u17CB',
    'Check #, Transaction ID': '\u1798\u17BC\u179B\u1794\u17D2\u1794\u1791\u17B6\u1793\u1794\u178F\u17D2\u179A #, \u179B\u17C1\u1781\u1794\u17D2\u179A\u178F\u17B7\u1794\u178F\u17D2\u178F\u17B7\u1780\u17B6\u179A',
    'No payments received yet.': '\u1798\u17B7\u1793\u1791\u17B6\u1793\u17CB\u1798\u17B6\u1793\u1780\u17B6\u179A\u1791\u1791\u17BD\u179B\u1794\u17D2\u179A\u17B6\u1780\u17CB\u17D4',
    'Insufficient Stock Warning': '\u1780\u17B6\u179A\u1796\u17D2\u179A\u1798\u17B6\u1793\u179F\u17D2\u178F\u17BB\u1780\u1798\u17B7\u1793\u1782\u17D2\u179A\u1794\u17CB\u1782\u17D2\u179A\u17B6\u1793\u17CB',
    'insufficient stock': '\u179F\u17D2\u178F\u17BB\u1780\u1798\u17B7\u1793\u1782\u17D2\u179A\u1794\u17CB\u1782\u17D2\u179A\u17B6\u1793\u17CB',
    'Confirm & Proceed': '\u1794\u1789\u17D2\u1787\u17B6\u1780\u17CB \u1793\u17B7\u1784 \u1794\u1793\u17D2\u178F',
    'INVOICE': '\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A',
    'UNPAID': '\u1798\u17B7\u1793\u1791\u17B6\u1793\u17CB\u1794\u1784\u17CB',
    'Bill To': '\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A\u178F\u17C2\u1791\u17C5',
    'Paid on': '\u1794\u17B6\u1793\u1794\u1784\u17CB\u1793\u17C5',
    'days overdue': '\u1790\u17D2\u1784\u17C3\u1795\u17BB\u178F\u1780\u17C6\u178E\u178F\u17CB',
    'Due today!': '\u1795\u17BB\u178F\u1780\u17C6\u178E\u178F\u17CB\u1790\u17D2\u1784\u17C3\u1793\u17C1\u17C7!',
    'days left': '\u1790\u17D2\u1784\u17C3\u1793\u17C5\u179F\u179B\u17CB',
    'days until due': '\u1790\u17D2\u1784\u17C3\u1798\u17BB\u1793\u1795\u17BB\u178F\u1780\u17C6\u178E\u178F\u17CB',
    'Thank you for your business!': '\u179F\u17BC\u1798\u17A2\u179A\u1782\u17BB\u178E\u179F\u1798\u17D2\u179A\u17B6\u1794\u17CB\u17A2\u17B6\u1787\u17B8\u179C\u1780\u1798\u17D2\u1798\u179A\u1794\u179F\u17CB\u17A2\u17D2\u1793\u1780!',
    'Tax ID:': '\u179B\u17C1\u1781\u1796\u1793\u17D2\u1792:',
    'Amount Paid': '\u1785\u17C6\u178E\u17BD\u1793\u1794\u17B6\u1793\u1794\u1784\u17CB',
    'Subtotal': '\u179F\u179A\u17BB\u1794\u179A\u17BD\u1798',
    'Discount': '\u1794\u1789\u17D2\u1785\u17BB\u17C7\u178F\u1798\u17D2\u179B\u17C3',

    // ─── PURCHASES PAGES (auto-added) ───
    'Bill # or vendor…': '\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A\u1791\u17B7\u1789 # \u17AC\u200B\u17A2\u17D2\u1793\u1780\u1795\u17D2\u1782\u178F\u17CB\u1795\u17D2\u1782\u1784\u17CB\u2026',
    'New Bill / Purchase': '\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A\u1791\u17B7\u1789\u1790\u17D2\u1798\u17B8',
    'Select Vendor': '\u1787\u17D2\u179A\u17BE\u179F\u179A\u17BE\u179F\u17A2\u17D2\u1793\u1780\u1795\u17D2\u1782\u178F\u17CB\u1795\u17D2\u1782\u1784\u17CB',
    'Unit Cost': '\u178F\u1798\u17D2\u179B\u17C3\u17AF\u1780\u178F\u17B6',
    'Pay Later (Owe)': '\u1794\u1784\u17CB\u1796\u17C1\u179B\u1780\u17D2\u179A\u17C4\u1799 (\u1787\u17C6\u1796\u17B6\u1780\u17CB)',
    'Record bill and pay when due date arrives': '\u1780\u178F\u17CB\u178F\u17D2\u179A\u17B6\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A \u1793\u17B7\u1784\u1794\u1784\u17CB\u1793\u17C5\u1796\u17C1\u179B\u1795\u17BB\u178F\u1780\u17C6\u178E\u178F\u17CB',
    'Pay immediately and mark bill as paid': '\u1794\u1784\u17CB\u1797\u17D2\u179B\u17B6\u1798 \u1793\u17B7\u1784\u179F\u1798\u17D2\u1782\u17B6\u179B\u17CB\u1790\u17B6\u1794\u17B6\u1793\u1794\u1784\u17CB',
    'Pay From Account *': '\u1794\u1784\u17CB\u1796\u17B8\u1782\u178E\u1793\u17B8 *',
    'Pay This Bill': '\u1794\u1784\u17CB\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A\u1793\u17C1\u17C7',
    'BILL': '\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A\u1791\u17B7\u1789',
    'Bill Details': '\u1796\u17D0\u178F\u17CC\u1798\u17B6\u1793\u179B\u1798\u17D2\u17A2\u17B7\u178F\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A\u1791\u17B7\u1789',
    'On Credit': '\u178F\u17B6\u1798\u17A5\u178E\u1791\u17B6\u1793',
    'Paid Now': '\u1794\u17B6\u1793\u1794\u1784\u17CB\u17A5\u17A1\u17BC\u179C',
    'Update Bill': '\u1792\u17D2\u179C\u17BE\u1794\u1785\u17D2\u1785\u17BB\u1794\u17D2\u1794\u1793\u17D2\u1793\u1797\u17B6\u1796\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A\u1791\u17B7\u1789',
    'Save Bill (Owe)': '\u179A\u1780\u17D2\u179F\u17B6\u1791\u17BB\u1780\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A (\u1787\u17C6\u1796\u17B6\u1780\u17CB)',
    'Payments': '\u1780\u17B6\u179A\u1794\u1784\u17CB\u1794\u17D2\u179A\u17B6\u1780\u17CB',
    'No payments made yet.': '\u1798\u17B7\u1793\u1791\u17B6\u1793\u17CB\u1798\u17B6\u1793\u1780\u17B6\u179A\u1794\u1784\u17CB\u1794\u17D2\u179A\u17B6\u1780\u17CB\u17D4',

    // ─── INVENTORY PAGES (auto-added) ───
    'Stock Adjustment': '\u1780\u17B6\u179A\u1780\u17C2\u178F\u1798\u17D2\u179A\u17BC\u179C\u179F\u17D2\u178F\u17BB\u1780',
    'Stock Out (Reduce)': '\u179F\u17D2\u178F\u17BB\u1780\u1785\u17C1\u1789 (\u1780\u17B6\u178F\u17CB\u1794\u1793\u17D2\u1790\u17C2\u1798)',
    'Stock In (Add)': '\u179F\u17D2\u178F\u17BB\u1780\u1785\u17BC\u179B (\u1794\u1793\u17D2\u1790\u17C2\u1798)',
    'Set to Exact Quantity': '\u1780\u17C6\u178E\u178F\u17CB\u1794\u179A\u17B7\u1798\u17B6\u178E\u1787\u17B6\u1780\u17CB\u179B\u17B6\u1780\u17CB',
    'Quantity': '\u1794\u179A\u17B7\u1798\u17B6\u178E',
    'Save Adjustment': '\u179A\u1780\u17D2\u179F\u17B6\u1791\u17BB\u1780\u1780\u17B6\u179A\u1780\u17C2\u178F\u1798\u17D2\u179A\u17BC\u179C',
    'No stock movements found.': '\u179A\u1780\u1798\u17B7\u1793\u1783\u17BE\u1789\u1785\u179B\u1793\u17B6\u179F\u17D2\u178F\u17BB\u1780\u17D4',
    'All Products': '\u1795\u179B\u17B7\u178F\u1795\u179B\u1791\u17B6\u17C6\u1784\u17A2\u179F\u17CB',
    'All Types': '\u1794\u17D2\u179A\u1797\u17C1\u1791\u1791\u17B6\u17C6\u1784\u17A2\u179F\u17CB',
    'No products yet.': '\u1798\u17B7\u1793\u1791\u17B6\u1793\u17CB\u1798\u17B6\u1793\u1795\u179B\u17B7\u178F\u1795\u179B\u17D4',
    'No services yet.': '\u1798\u17B7\u1793\u1791\u17B6\u1793\u17CB\u1798\u17B6\u1793\u179F\u17C1\u179C\u17B6\u1780\u1798\u17D2\u1798\u17D4',
    'Product (Inventory)': '\u1795\u179B\u17B7\u178F\u1795\u179B (\u179F\u17B6\u179A\u1796\u17BE\u1797\u17D0\u178E\u17D2\u178C)',
    'Tracks stock, COGS, asset account': '\u178F\u17B6\u1798\u178A\u17B6\u1793\u179F\u17D2\u178F\u17BB\u1780 \u178F\u1798\u17D2\u179B\u17C3\u1791\u17C6\u1793\u17B7\u1789\u179B\u1780\u17CB \u1782\u178E\u1793\u17B8\u1791\u17D2\u179A\u1796\u17D2\u1799\u179F\u1780\u1798\u17D2\u1798',
    'Service (Non-Inventory)': '\u179F\u17C1\u179C\u17B6\u1780\u1798\u17D2\u1798 (\u1798\u17B7\u1793\u1798\u17C2\u1793\u179F\u17B6\u179A\u1796\u17BE\u1797\u17D0\u178E\u17D2\u178C)',
    'Revenue only, no stock movement': '\u1785\u17C6\u178E\u17BC\u179B\u178F\u17C2\u1794\u17C9\u17BB\u178E\u17D2\u178E\u17C4\u17C7 \u1782\u17D2\u1798\u17B6\u1793\u1785\u179B\u1793\u17B6\u179F\u17D2\u178F\u17BB\u1780',
    'Item Type': '\u1794\u17D2\u179A\u1797\u17C1\u1791\u1792\u17B6\u178F\u17BB',
    'Sub-Category': '\u1794\u17D2\u179A\u1797\u17C1\u1791\u179A\u1784',
    'Advanced Classification': '\u1780\u17B6\u179A\u1785\u17C6\u178E\u17B6\u178F\u17CB\u1790\u17D2\u1793\u17B6\u1780\u17CB\u1780\u1798\u17D2\u179A\u17B7\u178F\u1781\u17D2\u1796\u179F\u17CB',
    'Revenue Type': '\u1794\u17D2\u179A\u1797\u17C1\u1791\u1785\u17C6\u178E\u17BC\u179B',
    'Cost Behavior': '\u17A5\u179A\u17B7\u1799\u17B6\u1794\u1790\u178F\u17D2\u178F\u1798\u17D2\u179B\u17C3',
    'Tax Type': '\u1794\u17D2\u179A\u1797\u17C1\u1791\u1796\u1793\u17D2\u1792',
    'Product Sales Revenue': '\u1785\u17C6\u178E\u17BC\u179B\u1780\u17B6\u179A\u179B\u1780\u17CB\u1795\u179B\u17B7\u178F\u1795\u179B',
    'Service Revenue': '\u1785\u17C6\u178E\u17BC\u179B\u179F\u17C1\u179C\u17B6\u1780\u1798\u17D2\u1798',
    'Contract Revenue': '\u1785\u17C6\u178E\u17BC\u179B\u1780\u17B7\u1785\u17D2\u1785\u179F\u1793\u17D2\u1799\u17B6',
    'Recurring Revenue': '\u1785\u17C6\u178E\u17BC\u179B\u1780\u17BE\u178F\u17A1\u17BE\u1784\u178A\u178A\u17C2\u179B\u17D7',
    'Project Revenue': '\u1785\u17C6\u178E\u17BC\u179B\u1782\u1798\u17D2\u179A\u17C4\u1784',
    'Direct Cost Item': '\u1792\u17B6\u178F\u17BB\u178F\u1798\u17D2\u179B\u17C3\u1795\u17D2\u1791\u17B6\u179B\u17CB',
    'Indirect Cost Item': '\u1792\u17B6\u178F\u17BB\u178F\u1798\u17D2\u179B\u17C3\u1794\u179A\u17C4\u1780\u17D2\u179F',
    'Billable Expense': '\u1785\u17C6\u178E\u17B6\u1799\u17A2\u17B6\u1785\u1785\u17C1\u1789\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A',
    'Taxable': '\u1787\u17B6\u1794\u17CB\u1796\u1793\u17D2\u1792',
    'Zero-rated': '\u17A2\u178F\u17D2\u179A\u17B6\u179F\u17BC\u1793\u17D2\u1799',
    'Exempt': '\u179B\u17C1\u1789\u179B\u17C3\u1796\u1793\u17D2\u1792',
    'Pricing & Markup': '\u178F\u1798\u17D2\u179B\u17C3 \u1793\u17B7\u1784 \u1780\u17B6\u179A\u1794\u1793\u17D2\u1790\u17C2\u1798\u178F\u1798\u17D2\u179B\u17C3',
    'Markup': '\u1780\u17B6\u179A\u1794\u1793\u17D2\u1790\u17C2\u1798\u178F\u1798\u17D2\u179B\u17C3',
    'Profit per unit:': '\u1785\u17C6\u178E\u17C1\u1789\u1780\u17D2\u1793\u17BB\u1784\u1798\u17BD\u1799\u17AF\u1780\u178F\u17B6:',
    'Margin:': '\u17A2\u178F\u17D2\u179A\u17B6\u1785\u17C6\u178E\u17C1\u1789:',
    'Product Name *': '\u1788\u17D2\u1798\u17C4\u17C7\u1795\u179B\u17B7\u178F\u1795\u179B *',
    'Opening Stock': '\u179F\u17D2\u178F\u17BB\u1780\u1785\u17B6\u1794\u17CB\u1795\u17D2\u178F\u17BE\u1798',
    '+ Add new category': '+ \u1794\u1793\u17D2\u1790\u17C2\u1798\u1794\u17D2\u179A\u1797\u17C1\u1791\u1790\u17D2\u1798\u17B8',
    'Reference / ID': '\u17AF\u1780\u179F\u17B6\u179A\u1799\u17C4\u1784 / \u179B\u17C1\u1781\u179F\u1798\u17D2\u1782\u17B6\u179B\u17CB',

    // ─── EXPENSES PAGES (auto-added) ───
    'Record Petty Cash Expense': '\u1780\u178F\u17CB\u178F\u17D2\u179A\u17B6\u1785\u17C6\u178E\u17B6\u1799\u179F\u17B6\u1785\u17CB\u1794\u17D2\u179A\u17B6\u1780\u17CB\u179A\u1793\u17D2\u1792\u178F\u17CB',
    'Choose category...': '\u1787\u17D2\u179A\u17BE\u179F\u179A\u17BE\u179F\u1794\u17D2\u179A\u1797\u17C1\u1791...',
    'What was this petty cash used for?': '\u179F\u17B6\u1785\u17CB\u1794\u17D2\u179A\u17B6\u1780\u17CB\u179A\u1793\u17D2\u1792\u178F\u17CB\u1793\u17C1\u17C7\u178F\u17D2\u179A\u17BC\u179C\u1794\u17B6\u1793\u1794\u17D2\u179A\u17BE\u179F\u1798\u17D2\u179A\u17B6\u1794\u17CB\u17A2\u17D2\u179C\u17B8?',
    'Receipt / Reference #': '\u1794\u1784\u17D2\u1780\u17B6\u1793\u17CB\u178A\u17C3 / \u17AF\u1780\u179F\u17B6\u179A\u1799\u17C4\u1784 #',
    'Record Expense': '\u1780\u178F\u17CB\u178F\u17D2\u179A\u17B6\u1785\u17C6\u178E\u17B6\u1799',
    'How It Works': '\u179A\u1794\u17C0\u1794\u178A\u17C6\u178E\u17BE\u179A\u1780\u17B6\u179A',
    'Paid from:': '\u1794\u1784\u17CB\u1796\u17B8:',
    'Payment method:': '\u179C\u17B7\u1792\u17B8\u1794\u1784\u17CB\u1794\u17D2\u179A\u17B6\u1780\u17CB:',
    'Expense account auto-selected by category': '\u1782\u178E\u1793\u17B8\u1785\u17C6\u178E\u17B6\u1799\u178F\u17D2\u179A\u17BC\u179C\u1794\u17B6\u1793\u1787\u17D2\u179A\u17BE\u179F\u179A\u17BE\u179F\u178A\u17C4\u1799\u179F\u17D2\u179C\u17D0\u1799\u1794\u17D2\u179A\u179C\u178F\u17D2\u178F\u17B7\u178F\u17B6\u1798\u1794\u17D2\u179A\u1797\u17C1\u1791',
    'Journal entry created automatically': '\u1794\u1789\u17D2\u1787\u17B8\u1780\u17C6\u178E\u178F\u17CB\u178F\u17D2\u179A\u17B6\u178F\u17D2\u179A\u17BC\u179C\u1794\u17B6\u1793\u1794\u1784\u17D2\u1780\u17BE\u178F\u178A\u17C4\u1799\u179F\u17D2\u179C\u17D0\u1799\u1794\u17D2\u179A\u179C\u178F\u17D2\u178F\u17B7',
    'Synced to cloud if enabled': '\u1792\u17D2\u179C\u17BE\u179F\u1798\u1780\u17B6\u179B\u1780\u1798\u17D2\u1798\u1796\u1796\u1780\u1794\u17D2\u179A\u179F\u17B7\u1793\u1794\u17BE\u179C\u17B6\u1794\u17BE\u1780\u178A\u17C6\u178E\u17BE\u179A\u1780\u17B6\u179A',
    'Petty Cash Categories': '\u1794\u17D2\u179A\u1797\u17C1\u1791\u179F\u17B6\u1785\u17CB\u1794\u17D2\u179A\u17B6\u1780\u17CB\u179A\u1793\u17D2\u1792\u178F\u17CB',

    // ─── JOURNAL PAGES (auto-added) ───
    'Entry description': '\u1780\u17B6\u179A\u1796\u178E\u17CC\u1793\u17B6\u1794\u1789\u17D2\u1787\u17B8',
    'Journal Lines': '\u1794\u1793\u17D2\u1791\u17B6\u178F\u17CB\u1794\u1789\u17D2\u1787\u17B8',
    'Select Account': '\u1787\u17D2\u179A\u17BE\u179F\u179A\u17BE\u179F\u1782\u178E\u1793\u17B8',
    'Totals:': '\u179F\u179A\u17BB\u1794:',
    'Save as Draft': '\u179A\u1780\u17D2\u179F\u17B6\u1791\u17BB\u1780\u1787\u17B6\u179F\u17C1\u1785\u1780\u17D2\u178F\u17B8\u1796\u17D2\u179A\u17B6\u1784',
    'Save & Post': '\u179A\u1780\u17D2\u179F\u17B6\u1791\u17BB\u1780 \u1793\u17B7\u1784 \u1795\u17D2\u179F\u17B6\u1799',
    'Reversing Entry': '\u1794\u1789\u17D2\u1787\u17B8\u1794\u1789\u17D2\u1785\u17D2\u179A\u17B6\u179F',

    // ─── FISCAL PAGES (auto-added) ───
    'Year-End Closing': '\u1794\u17B7\u1791\u1785\u17BB\u1784\u1786\u17D2\u1793\u17B6\u17C6',
    'Locked By': '\u1785\u17B6\u1780\u17CB\u179F\u17C4\u178A\u17C4\u1799',
    'Locked At': '\u1785\u17B6\u1780\u17CB\u179F\u17C4\u1793\u17C5',

    // ─── AUDIT PAGE (auto-added) ───
    'Tracking all system activity across all users': '\u178F\u17B6\u1798\u178A\u17B6\u1793\u179F\u1780\u1798\u17D2\u1798\u1797\u17B6\u1796\u1794\u17D2\u179A\u1796\u17D0\u1793\u17D2\u1792\u1791\u17B6\u17C6\u1784\u17A2\u179F\u17CB\u1787\u17B6\u1785\u17D2\u179A\u17BE\u1793\u17A2\u17D2\u1793\u1780\u1794\u17D2\u179A\u17BE\u1794\u17D2\u179A\u17B6\u179F\u17CB',
    'Your personal activity history': '\u1794\u17D2\u179A\u179C\u178F\u17D2\u178F\u17B7\u179F\u1780\u1798\u17D2\u1798\u1797\u17B6\u1796\u1795\u17D2\u1791\u17B6\u179B\u17CB\u1781\u17D2\u179B\u17BD\u1793\u179A\u1794\u179F\u17CB\u17A2\u17D2\u1793\u1780',
    'All Actions': '\u179F\u1780\u1798\u17D2\u1798\u1797\u17B6\u1796\u1791\u17B6\u17C6\u1784\u17A2\u179F\u17CB',
    'Label, details, or user name…': '\u179F\u17D2\u179B\u17B6\u1780 \u1796\u17D0\u178F\u17CC\u1798\u17B6\u1793\u179B\u1798\u17D2\u17A2\u17B7\u178F \u17AC\u1788\u17D2\u1798\u17C4\u17C7\u17A2\u17D2\u1793\u1780\u1794\u17D2\u179A\u17BE\u1794\u17D2\u179A\u17B6\u179F\u17CB\u2026',

    // ─── BUDGET PAGE (auto-added) ───
    'Create Budget': '\u1794\u1784\u17D2\u1780\u17BE\u178F\u1790\u179C\u17B7\u1780\u17B6',
    'No budgets set for': '\u1798\u17B7\u1793\u1798\u17B6\u1793\u1790\u179C\u17B7\u1780\u17B6\u1780\u17C6\u178E\u178F\u17CB\u179F\u1798\u17D2\u179A\u17B6\u1794\u17CB',

    // ─── CHAT PAGE (auto-added) ───
    'Chat with our support team for assistance': '\u1787\u17C6\u1793\u17BD\u1789\u1787\u17B6\u1798\u17BD\u1799\u1780\u17D2\u179A\u17BB\u1798\u1787\u17C6\u1793\u17BD\u1799\u179A\u1794\u179F\u17CB\u1799\u17BE\u1784\u179F\u1798\u17D2\u179A\u17B6\u1794\u17CB\u1787\u17C6\u1793\u17BD\u1799',
    'Welcome to Live Chat Support': '\u179F\u17BC\u1798\u179F\u17D2\u179C\u17B6\u1782\u1798\u1793\u17CD\u1798\u1780\u1780\u17B6\u1793\u17CB\u1787\u17C6\u1793\u17BD\u1799\u1795\u17D2\u1791\u17B6\u179B\u17CB',
    'Send a message and our support team will respond as soon as possible.': '\u1795\u17D2\u1789\u17BE\u179F\u17B6\u179A \u1793\u17B7\u1784\u1780\u17D2\u179A\u17BB\u1798\u1787\u17C6\u1793\u17BD\u1799\u179A\u1794\u179F\u17CB\u1799\u17BE\u1784\u1793\u17B9\u1784\u1786\u17D2\u179B\u17BE\u1799\u178F\u1794\u17A2\u179F\u17CB\u17A0\u17BE\u1791\u17B6\u1793\u17CB\u17D4',
    'Support Team': '\u1780\u17D2\u179A\u17BB\u1798\u1787\u17C6\u1793\u17BD\u1799',
    'Type your message...': '\u179C\u17B6\u1799\u179F\u17B6\u179A\u179A\u1794\u179F\u17CB\u17A2\u17D2\u1793\u1780...',

    // ─── COMMON SHARED (auto-added) ───
    'matching filters': '\u178F\u17D2\u179A\u17BC\u179C\u178F\u17B6\u1798\u178F\u1798\u17D2\u179A\u1784',
    'customer': '\u17A2\u178F\u17B7\u1790\u17B7\u1787\u1793',
    'customers': '\u17A2\u178F\u17B7\u1790\u17B7\u1787\u1793',
    'vendor': '\u17A2\u17D2\u1793\u1780\u1795\u17D2\u1782\u178F\u17CB\u1795\u17D2\u1782\u1784\u17CB',
    'vendors': '\u17A2\u17D2\u1793\u1780\u1795\u17D2\u1782\u178F\u17CB\u1795\u17D2\u1782\u1784\u17CB',
    'movement': '\u1785\u179B\u1793\u17B6',
    'movements': '\u1785\u179B\u1793\u17B6',
    'event': '\u1796\u17C1\u179B\u179C\u17C1\u179B\u17B6',
    'events': '\u1796\u17C1\u179B\u179C\u17C1\u179B\u17B6',
    'overdue invoice': '\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A\u1795\u17BB\u178F\u1780\u17C6\u178E\u178F\u17CB',
    'overdue invoices': '\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A\u1795\u17BB\u178F\u1780\u17C6\u178E\u178F\u17CB',
    'overdue bill': '\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A\u1791\u17B7\u1789\u1795\u17BB\u178F\u1780\u17C6\u178E\u178F\u17CB',
    'overdue bills': '\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A\u1791\u17B7\u1789\u1795\u17BB\u178F\u1780\u17C6\u178E\u178F\u17CB',
    'OVERDUE!': '\u1795\u17BB\u178F\u1780\u17C6\u178E\u178F\u17CB!',
    'Expense #': '\u1785\u17C6\u178E\u17B6\u1799 #',
    'Pinned': '\u1794\u17B6\u1793\u1781\u17D2\u1791\u17B6\u179F\u17CB',
    'Accounts': '\u1782\u178E\u1793\u17B8',
    'Asset Accounts': '\u1782\u178E\u1793\u17B8\u1791\u17D2\u179A\u1796\u17D2\u1799\u179F\u1780\u1798\u17D2\u1798',
    'Liability Accounts': '\u1782\u178E\u1793\u17B8\u1794\u17C6\u178E\u17BB\u179B',
    'Equity Accounts': '\u1782\u178E\u1793\u17B8\u1798\u17BC\u179B\u1792\u1793',
    'Revenue Accounts': '\u1782\u178E\u1793\u17B8\u1785\u17C6\u178E\u17BC\u179B',
    'Expense Accounts': '\u1782\u178E\u1793\u17B8\u1785\u17C6\u178E\u17B6\u1799',
    'Service Item': '\u1792\u17B6\u178F\u17BB\u179F\u17C1\u179C\u17B6\u1780\u1798\u17D2\u1798',
    'Revenue only — no stock tracking, no COGS': '\u1785\u17C6\u178E\u17BC\u179B\u178F\u17C2\u1794\u17C9\u17BB\u178E\u17D2\u178E\u17C4\u17C7 \u2014 \u1782\u17D2\u1798\u17B6\u1793\u178F\u17B6\u1798\u178A\u17B6\u1793\u179F\u17D2\u178F\u17BB\u1780 \u1782\u17D2\u1798\u17B6\u1793\u178F\u1798\u17D2\u179B\u17C3\u1791\u17C6\u1793\u17B7\u1789\u179B\u1780\u17CB',
    'Set up your industry': '\u179A\u17C0\u1794\u1785\u17C6\u17A7\u179F\u17D2\u179F\u17B6\u17A0\u1780\u1798\u17D2\u1798\u179A\u1794\u179F\u17CB\u17A2\u17D2\u1793\u1780',
    'Pay now': '\u1794\u1784\u17CB\u17A5\u17A1\u17BC\u179C',
    'No specific bill': '\u1782\u17D2\u1798\u17B6\u1793\u179C\u17B7\u1780\u17D2\u1780\u1799\u1794\u178F\u17D2\u179A\u1791\u17B7\u1789\u1787\u17B6\u1780\u17CB\u179B\u17B6\u1780\u17CB',
    'Record Payment Made': '\u1780\u178F\u17CB\u178F\u17D2\u179A\u17B6\u1780\u17B6\u179A\u1794\u1784\u17CB\u1794\u17D2\u179A\u17B6\u1780\u17CB',
    'Customer *': '\u17A2\u178F\u17B7\u1790\u17B7\u1787\u1793 *',
    'Vendor *': '\u17A2\u17D2\u1793\u1780\u1795\u17D2\u1782\u178F\u17CB\u1795\u17D2\u1782\u1784\u17CB *',
    'Date *': '\u1780\u17B6\u179B\u1794\u179A\u17B7\u1785\u17D2\u1786\u17C1\u1791 *',
    'Amount *': '\u1785\u17C6\u178E\u17BD\u1793\u1791\u17B9\u1780\u1794\u17D2\u179A\u17B6\u1780\u17CB *',

};

// ─── Brand names that should NEVER be translated ───────────────
const BRAND_TERMS = [
    'KH Accounting Software Enterprise',
    'KH Accounting Software',
    'Accounting Software',
    'Enterprise',
    'KH.',
    'KH',
];

/**
 * Get the current language preference
 */
function getLanguage() {
    return localStorage.getItem('kh-lang') || 'en';
}

/**
 * Set language preference and reload
 */
function setLanguage(lang) {
    localStorage.setItem('kh-lang', lang);
    // Also notify server via a quick fetch
    fetch('/auth/set-language', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
        },
        body: JSON.stringify({ language: lang })
    }).catch(() => {});
    location.reload();
}

/**
 * Check if a string is or contains a brand term that should be preserved
 */
function isBrandOnly(text) {
    const trimmed = text.trim();
    return BRAND_TERMS.some(b => trimmed === b);
}

/**
 * Translate a single text string from English to Khmer
 */
function translateText(text) {
    if (!text || typeof text !== 'string') return text;

    const trimmed = text.trim();
    if (!trimmed) return text;

    // Don't translate brand-only strings
    if (isBrandOnly(trimmed)) return text;

    // Exact match first
    if (KH_TRANSLATIONS[trimmed]) {
        return text.replace(trimmed, KH_TRANSLATIONS[trimmed]);
    }

    // Try translating the text with partial matches for longer strings
    let result = text;
    // Sort keys by length (longest first) to avoid partial replacements
    const sortedKeys = Object.keys(KH_TRANSLATIONS).sort((a, b) => b.length - a.length);

    for (const key of sortedKeys) {
        if (isBrandOnly(key)) continue;
        if (result.includes(key)) {
            result = result.split(key).join(KH_TRANSLATIONS[key]);
        }
    }

    return result;
}

/**
 * Translate all text nodes within an element
 */
function translateElement(root) {
    if (getLanguage() !== 'km') return;

    const walker = document.createTreeWalker(
        root,
        NodeFilter.SHOW_TEXT,
        {
            acceptNode: function(node) {
                // Skip script and style elements
                const parent = node.parentElement;
                if (!parent) return NodeFilter.FILTER_REJECT;
                const tag = parent.tagName;
                if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'CODE' || tag === 'PRE') {
                    return NodeFilter.FILTER_REJECT;
                }
                // Skip if parent has data-no-translate
                if (parent.closest('[data-no-translate]')) {
                    return NodeFilter.FILTER_REJECT;
                }
                return NodeFilter.FILTER_ACCEPT;
            }
        }
    );

    const textNodes = [];
    while (walker.nextNode()) {
        textNodes.push(walker.currentNode);
    }

    for (const node of textNodes) {
        const original = node.nodeValue;
        if (!original || !original.trim()) continue;
        const translated = translateText(original);
        if (translated !== original) {
            node.nodeValue = translated;
        }
    }

    // Translate placeholder attributes
    root.querySelectorAll('[placeholder]').forEach(el => {
        if (el.closest('[data-no-translate]')) return;
        const orig = el.getAttribute('placeholder');
        const translated = translateText(orig);
        if (translated !== orig) {
            el.setAttribute('placeholder', translated);
        }
    });

    // Translate title attributes
    root.querySelectorAll('[title]').forEach(el => {
        if (el.closest('[data-no-translate]')) return;
        const orig = el.getAttribute('title');
        const translated = translateText(orig);
        if (translated !== orig) {
            el.setAttribute('title', translated);
        }
    });

    // Translate aria-label attributes
    root.querySelectorAll('[aria-label]').forEach(el => {
        if (el.closest('[data-no-translate]')) return;
        const orig = el.getAttribute('aria-label');
        const translated = translateText(orig);
        if (translated !== orig) {
            el.setAttribute('aria-label', translated);
        }
    });
}

/**
 * Translate the page title
 */
function translatePageTitle() {
    if (getLanguage() !== 'km') return;
    const title = document.title;
    // Keep brand name in title but translate the rest
    let newTitle = title;
    const sortedKeys = Object.keys(KH_TRANSLATIONS).sort((a, b) => b.length - a.length);
    for (const key of sortedKeys) {
        if (BRAND_TERMS.includes(key)) continue;
        if (newTitle.includes(key)) {
            newTitle = newTitle.split(key).join(KH_TRANSLATIONS[key]);
        }
    }
    if (newTitle !== title) {
        document.title = newTitle;
    }
}

/**
 * Set up Khmer font if language is Khmer
 */
function setupKhmerFont() {
    if (getLanguage() !== 'km') return;

    // Add Khmer font
    const link = document.createElement('link');
    link.href = 'https://fonts.googleapis.com/css2?family=Battambang:wght@300;400;700;900&family=Noto+Sans+Khmer:wght@300;400;500;600;700;800&display=swap';
    link.rel = 'stylesheet';
    document.head.appendChild(link);

    // Apply Khmer font to body (but not to brand elements)
    const style = document.createElement('style');
    style.textContent = `
        body:not([data-no-translate]),
        .sidebar-link span,
        .sidebar-section,
        .page-content,
        .top-navbar,
        .auth-card,
        .auth-brand .brand-tagline,
        .auth-brand .brand-features,
        .trust-badge .tb-label,
        .about-link,
        .kpi-label, .kpi-value, .kpi-sub, .kpi-change,
        .dash-title, .dash-subtitle,
        .btn, .form-label, .form-control,
        .dropdown-menu, .dropdown-item,
        .table, th, td,
        .modal, .modal-title, .modal-body,
        .card, .card-body, .card-title, .card-header,
        .alert, .badge,
        .toast-msg,
        h1, h2, h3, h4, h5, h6,
        p, span, label, a, li, div {
            font-family: 'Noto Sans Khmer', 'Battambang', 'Inter', sans-serif !important;
        }

        /* Keep brand elements in Inter font */
        .brand-monogram,
        .brand-name,
        .brand-edition,
        .auth-brand-name,
        .auth-brand-edition,
        .logo-kh,
        [data-no-translate],
        [data-no-translate] * {
            font-family: 'Inter', sans-serif !important;
        }

        /* Adjust font sizes slightly for Khmer text */
        .sidebar-link span {
            font-size: 0.82rem;
        }

        /* Language selector styling */
        .lang-selector {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 0.78rem;
            font-weight: 600;
            cursor: pointer;
            border: 1.5px solid var(--border, rgba(255,255,255,.1));
            background: var(--body-bg, transparent);
            color: var(--text-secondary, #64748b);
            transition: all 0.2s ease;
        }
        .lang-selector:hover {
            border-color: #3b82f6;
            color: #3b82f6;
        }
        .lang-selector img,
        .lang-selector .lang-flag {
            width: 18px;
            height: 14px;
            border-radius: 2px;
            object-fit: cover;
        }
    `;
    document.head.appendChild(style);
}

/**
 * Initialize the translation system
 */
function initTranslation() {
    setupKhmerFont();
    translateElement(document.body);
    translatePageTitle();

    // Watch for dynamic DOM changes (AJAX content, modals, etc.)
    const observer = new MutationObserver(mutations => {
        if (getLanguage() !== 'km') return;
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    translateElement(node);
                } else if (node.nodeType === Node.TEXT_NODE && node.nodeValue?.trim()) {
                    const translated = translateText(node.nodeValue);
                    if (translated !== node.nodeValue) {
                        node.nodeValue = translated;
                    }
                }
            }
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
}

// Run when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTranslation);
} else {
    initTranslation();
}
