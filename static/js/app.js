// ═══════════════════════════════════════════════════════════
//  KH Accounting Software Enterprise – Modern UI JS  (2026)
// ═══════════════════════════════════════════════════════════

// ─── Sidebar Toggle ───────────────────────────────────────
(function initSidebar() {
    var sidebar = document.getElementById('sidebar');
    var overlay = document.getElementById('sidebarOverlay');
    var toggle = document.getElementById('sidebarToggle');

    function openSidebar() {
        sidebar?.classList.add('show');
        overlay?.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
    function closeSidebar() {
        sidebar?.classList.remove('show');
        overlay?.classList.remove('active');
        document.body.style.overflow = '';
    }

    toggle?.addEventListener('click', function () {
        if (sidebar?.classList.contains('show')) {
            closeSidebar();
        } else {
            openSidebar();
        }
    });

    overlay?.addEventListener('click', closeSidebar);

    // Close sidebar when clicking a link on mobile/tablet
    sidebar?.querySelectorAll('.sidebar-link').forEach(function(link) {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 992) closeSidebar();
        });
    });

    // Close on resize to desktop
    window.addEventListener('resize', function() {
        if (window.innerWidth > 992) closeSidebar();
    });

    // Close on outside click (fallback)
    document.addEventListener('click', function (e) {
        if (window.innerWidth <= 992 && sidebar?.classList.contains('show') &&
            !sidebar.contains(e.target) && !toggle?.contains(e.target) && e.target !== overlay) {
            closeSidebar();
        }
    });
})();

// ─── Dark Mode Toggle ────────────────────────────────────
(function initTheme() {
    const html = document.documentElement;
    const btn = document.getElementById('themeToggle');
    const saved = localStorage.getItem('accubooks-theme') || 'light';
    html.setAttribute('data-theme', saved);
    updateThemeIcon(saved);

    btn?.addEventListener('click', function () {
        const current = html.getAttribute('data-theme');
        const next = current === 'light' ? 'dark' : 'light';
        html.setAttribute('data-theme', next);
        localStorage.setItem('accubooks-theme', next);
        updateThemeIcon(next);
    });

    function updateThemeIcon(theme) {
        if (!btn) return;
        btn.innerHTML = theme === 'dark'
            ? '<i class="bi bi-sun-fill"></i>'
            : '<i class="bi bi-moon-stars-fill"></i>';
    }
})();

// ─── Toast Auto-Dismiss ──────────────────────────────────
document.querySelectorAll('.toast-msg[data-auto-dismiss]').forEach(function (el) {
    const delay = parseInt(el.dataset.autoDismiss) || 5000;
    setTimeout(function () {
        el.style.opacity = '0';
        el.style.transform = 'translateX(30px)';
        el.style.transition = 'all 0.3s ease';
        setTimeout(function () { el.remove(); }, 350);
    }, delay);
});

// ─── Command Palette / Global Search ─────────────────────
var cmdBackdrop = document.getElementById('cmdBackdrop');
var cmdInput = document.getElementById('cmdInput');
var cmdResults = document.getElementById('cmdResults');
var cmdItems = [];

function openCommandPalette() {
    cmdBackdrop?.classList.add('open');
    cmdInput?.focus();
    cmdItems = Array.from(cmdResults?.querySelectorAll('.cmd-item') || []);
}
function closeCommandPalette() {
    cmdBackdrop?.classList.remove('open');
    if (cmdInput) cmdInput.value = '';
    cmdItems.forEach(function (item) { item.style.display = ''; });
}
// Keyboard shortcut: Ctrl+K
document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        cmdBackdrop?.classList.contains('open') ? closeCommandPalette() : openCommandPalette();
    }
    if (e.key === 'Escape') closeCommandPalette();
});
// Click backdrop to close
cmdBackdrop?.addEventListener('click', function (e) {
    if (e.target === cmdBackdrop) closeCommandPalette();
});

// ─── Format Currency ──────────────────────────────────────
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
}

// ─── Dynamic Journal Entry Lines ──────────────────────────
function addJournalLine() {
    const tbody = document.getElementById('journalLines');
    if (!tbody) return;
    const rowCount = tbody.rows.length;
    const row = tbody.insertRow();
    row.innerHTML = `
        <td>
            <select name="lines-${rowCount}-account_id" class="form-select" required>
                <option value="">Select Account</option>
                ${window.accountOptions || ''}
            </select>
        </td>
        <td><input type="text" name="lines-${rowCount}-description" class="form-control" placeholder="Description"></td>
        <td><input type="number" name="lines-${rowCount}-debit" class="form-control debit-input" step="0.01" min="0" value="0" onchange="updateJournalTotals()"></td>
        <td><input type="number" name="lines-${rowCount}-credit" class="form-control credit-input" step="0.01" min="0" value="0" onchange="updateJournalTotals()"></td>
        <td><button type="button" class="btn btn-sm btn-outline-danger" onclick="removeJournalLine(this)"><i class="bi bi-trash"></i></button></td>
    `;
    document.getElementById('lineCount').value = rowCount + 1;
}
function removeJournalLine(btn) {
    btn.closest('tr').remove();
    updateJournalTotals();
    reindexJournalLines();
}
function reindexJournalLines() {
    const tbody = document.getElementById('journalLines');
    if (!tbody) return;
    Array.from(tbody.rows).forEach((row, idx) => {
        row.querySelectorAll('[name]').forEach(input => {
            input.name = input.name.replace(/lines-\d+-/, `lines-${idx}-`);
        });
    });
    document.getElementById('lineCount').value = tbody.rows.length;
}
function updateJournalTotals() {
    let totalDebit = 0, totalCredit = 0;
    document.querySelectorAll('.debit-input').forEach(el => { totalDebit += parseFloat(el.value) || 0; });
    document.querySelectorAll('.credit-input').forEach(el => { totalCredit += parseFloat(el.value) || 0; });
    const debitTotal = document.getElementById('totalDebit');
    const creditTotal = document.getElementById('totalCredit');
    const diffEl = document.getElementById('difference');
    if (debitTotal) debitTotal.textContent = totalDebit.toFixed(2);
    if (creditTotal) creditTotal.textContent = totalCredit.toFixed(2);
    if (diffEl) {
        const diff = Math.abs(totalDebit - totalCredit);
        diffEl.textContent = diff.toFixed(2);
        diffEl.className = diff < 0.01 ? 'text-success fw-bold' : 'text-danger fw-bold';
    }
}

// ─── Dynamic Invoice / Bill Lines ─────────────────────────
function addInvoiceLine() {
    const tbody = document.getElementById('invoiceLines');
    if (!tbody) return;
    const rowCount = tbody.rows.length;
    const row = tbody.insertRow();
    const svcBiz = typeof isServiceBusiness !== 'undefined' && isServiceBusiness;
    row.innerHTML = `
        <td>
            <select name="items-${rowCount}-product_id" class="form-select product-select" onchange="onProductSelect(this, ${rowCount})">
                <option value="">Select ${svcBiz ? 'Service' : 'Product'}</option>
                ${window.productOptions || ''}
            </select>
        </td>
        <td><input type="text" name="items-${rowCount}-description" class="form-control" required></td>
        ${svcBiz ? '' : `<td><span class="badge bg-secondary item-type-badge" id="item-type-${rowCount}">—</span></td>`}
        <td>
            <input type="number" name="items-${rowCount}-quantity" class="form-control qty-input" step="0.01" min="0" value="1" onchange="updateLineAmount(${rowCount})">
            ${svcBiz ? '' : `<div class="stock-warning text-danger small" id="stock-warn-${rowCount}"></div>`}
        </td>
        <td><input type="number" name="items-${rowCount}-unit_price" class="form-control price-input" step="0.01" min="0" value="0" onchange="updateLineAmount(${rowCount})"></td>
        <td><input type="number" name="items-${rowCount}-amount" class="form-control amount-input" step="0.01" readonly></td>
        <td><button type="button" class="btn btn-sm btn-outline-danger" onclick="removeInvoiceLine(this)"><i class="bi bi-trash"></i></button></td>
    `;
    document.getElementById('itemCount').value = rowCount + 1;
    // Apply current product filter (product businesses only)
    if (!svcBiz && typeof currentFilter !== 'undefined' && currentFilter !== 'all') {
        var sel = row.querySelector('.product-select');
        if (sel) {
            sel.querySelectorAll('option[data-item-type]').forEach(function(opt) {
                opt.style.display = (opt.getAttribute('data-item-type') === currentFilter) ? '' : 'none';
            });
        }
    }
}
function removeInvoiceLine(btn) {
    btn.closest('tr').remove();
    reindexInvoiceLines();
    updateInvoiceTotal();
}
function reindexInvoiceLines() {
    const tbody = document.getElementById('invoiceLines');
    if (!tbody) return;
    Array.from(tbody.rows).forEach((row, idx) => {
        row.querySelectorAll('[name]').forEach(input => {
            input.name = input.name.replace(/items-\d+-/, `items-${idx}-`);
        });
        const sel = row.querySelector('.product-select');
        if (sel) sel.setAttribute('onchange', `onProductSelect(this, ${idx})`);
        row.querySelectorAll('.qty-input, .price-input').forEach(inp => {
            inp.setAttribute('onchange', `updateLineAmount(${idx})`);
        });
        const warnEl = row.querySelector('.stock-warning');
        if (warnEl) warnEl.id = `stock-warn-${idx}`;
        const badgeEl = row.querySelector('.item-type-badge');
        if (badgeEl) badgeEl.id = `item-type-${idx}`;
    });
    document.getElementById('itemCount').value = tbody.rows.length;
}
function updateLineAmount(idx) {
    const qty = parseFloat(document.querySelector(`[name="items-${idx}-quantity"]`)?.value) || 0;
    const price = parseFloat(document.querySelector(`[name="items-${idx}-unit_price"]`)?.value) || 0;
    const amountField = document.querySelector(`[name="items-${idx}-amount"]`);
    if (amountField) amountField.value = (qty * price).toFixed(2);
    updateInvoiceTotal();
    if (typeof checkLineStock === 'function') checkLineStock(idx);
}
function updateInvoiceTotal() {
    let subtotal = 0;
    document.querySelectorAll('.amount-input').forEach(el => { subtotal += parseFloat(el.value) || 0; });
    const subtotalEl = document.getElementById('subtotal');
    const taxRateEl = document.getElementById('tax_rate');
    const taxAmountEl = document.getElementById('taxAmount');
    const discountEl = document.getElementById('discount_amount');
    const totalEl = document.getElementById('grandTotal');
    if (subtotalEl) subtotalEl.textContent = subtotal.toFixed(2);
    const taxRate = parseFloat(taxRateEl?.value) || 0;
    const taxAmount = subtotal * (taxRate / 100);
    if (taxAmountEl) taxAmountEl.textContent = taxAmount.toFixed(2);
    const discount = parseFloat(discountEl?.value) || 0;
    const total = subtotal + taxAmount - discount;
    if (totalEl) totalEl.textContent = total.toFixed(2);
}
function onProductSelect(selectEl, idx) {
    const productId = selectEl.value;
    if (!productId || !window.productData) return;
    const product = window.productData[productId];
    const svcBiz = typeof isServiceBusiness !== 'undefined' && isServiceBusiness;
    if (product) {
        document.querySelector(`[name="items-${idx}-description"]`).value = product.name;
        document.querySelector(`[name="items-${idx}-unit_price"]`).value = product.price;
        // Update type badge (product businesses only)
        if (!svcBiz) {
            var badge = document.getElementById('item-type-' + idx);
            if (badge) {
                if (product.isService || product.itemType === 'service') {
                    badge.textContent = 'SVC';
                    badge.className = 'badge bg-success item-type-badge';
                } else {
                    badge.textContent = 'PRD';
                    badge.className = 'badge bg-primary item-type-badge';
                }
            }
        }
        updateLineAmount(idx);
        if (!svcBiz && typeof checkLineStock === 'function') checkLineStock(idx);
    } else {
        if (!svcBiz) {
            var badge = document.getElementById('item-type-' + idx);
            if (badge) { badge.textContent = '—'; badge.className = 'badge bg-secondary item-type-badge'; }
        }
    }
}

// ─── Confirm Deletes ──────────────────────────────────────
document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', function (e) {
        if (!confirm(this.dataset.confirm)) e.preventDefault();
    });
});

// ─── Chart.js Global Dark-Aware Defaults ──────────────────
function getChartTextColor() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? '#94a3b8' : '#64748b';
}
function getChartGridColor() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? 'rgba(148,163,184,0.1)' : 'rgba(0,0,0,0.05)';
}

// ─── PDF Export (via html2pdf.js) ─────────────────────────
function exportPDF(filename) {
    // Prefer the branded invoice area if it exists, otherwise fall back to page-content
    var el = document.getElementById('invoiceArea') || document.querySelector('.page-content');
    if (!el) return;
    // Temporarily hide elements marked no-print
    var noPrint = document.querySelectorAll('.no-print');
    noPrint.forEach(function(n) { n.dataset.prevDisplay = n.style.display; n.style.display = 'none'; });
    var opt = {
        margin:       [10, 10, 10, 10],
        filename:     (filename || 'document') + '.pdf',
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };
    html2pdf().set(opt).from(el).save().then(function() {
        noPrint.forEach(function(n) { n.style.display = n.dataset.prevDisplay || ''; });
    });
}

function exportReportPDF(title) {
    var el = document.querySelector('.card') || document.querySelector('.page-content');
    if (!el) return;
    var opt = {
        margin:       [10, 10, 10, 10],
        filename:     (title || 'report') + '.pdf',
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };
    html2pdf().set(opt).from(el).save();
}

// ─── Live Search in Command Palette ───────────────────────
var searchTimeout = null;
cmdInput?.addEventListener('input', function () {
    var q = this.value.trim();
    // Filter static items
    cmdItems.forEach(function (item) {
        var text = item.textContent.toLowerCase();
        item.style.display = text.includes(q.toLowerCase()) ? '' : 'none';
    });
    // Live search API
    if (q.length >= 2) {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(function () {
            fetch('/api/search?q=' + encodeURIComponent(q))
                .then(function(r) { return r.json(); })
                .then(function(results) {
                    // Remove old live results
                    cmdResults?.querySelectorAll('.cmd-live').forEach(function(el) { el.remove(); });
                    results.forEach(function(r) {
                        var div = document.createElement('div');
                        div.className = 'cmd-item cmd-live';
                        div.innerHTML = '<i class="bi ' + r.icon + '"></i> ' + r.label + ' <span class="cmd-shortcut">' + r.type + '</span>';
                        div.onclick = function() { window.location = r.url; };
                        cmdResults?.appendChild(div);
                    });
                });
        }, 250);
    } else {
        cmdResults?.querySelectorAll('.cmd-live').forEach(function(el) { el.remove(); });
    }
});
