<!DOCTYPE html>
<html lang="az">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PTPK | İcazəli İstifadəçi Siyahısı (Admin)</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: #f4f6f9; color: #333; padding: 40px 20px; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #f0f0f0; padding-bottom: 20px; margin-bottom: 25px; }
        .header h1 { font-size: 24px; color: #1e293b; }
        .logout-btn { background: #ef4444; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500; transition: 0.2s; }
        .logout-btn:hover { background: #dc2626; }
        .form-group { display: flex; gap: 15px; margin-bottom: 25px; background: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; }
        input, select { padding: 10px 14px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; outline: none; }
        input[type="email"] { flex: 2; }
        input[type="text"] { flex: 1; }
        select { flex: 0.5; }
        .add-btn { background: #2563eb; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: 600; transition: 0.2s; }
        .add-btn:hover { background: #1d4ed8; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { text-align: left; padding: 12px 16px; border-bottom: 1px solid #e2e8f0; font-size: 14px; }
        th { background-color: #f8fafc; color: #64748b; font-weight: 600; }
        tr:hover { background-color: #fcfdfe; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
        .badge.admin { background: #dbeafe; color: #1e40af; }
        .badge.user { background: #e2e8f0; color: #334155; }
        .badge.komissiya { background: #dcfce7; color: #15803d; }
        .role-select { padding: 4px 8px; font-size: 12px; border-radius: 4px; }
        .delete-btn { background: none; border: none; color: #ef4444; cursor: pointer; font-weight: 500; }
        .delete-btn:hover { text-decoration: underline; }
        .loading-row, .empty-row { text-align: center; color: #94a3b8; padding: 24px; font-size: 13px; }
        .toast { position: fixed; bottom: 24px; right: 24px; background: #1e293b; color: #fff; padding: 12px 18px; border-radius: 8px; font-size: 13px; font-weight: 500; box-shadow: 0 6px 16px rgba(0,0,0,0.2); display: none; z-index: 100; }
        .toast.error { background: #dc2626; }
        .add-btn:disabled { background: #93c5fd; cursor: not-allowed; }

        @media (max-width: 640px) {
            body { padding: 16px 10px; }
            .container { padding: 16px; border-radius: 10px; }
            .header { flex-wrap: wrap; gap: 10px; }
            .header h1 { font-size: 18px; }
            .form-group { flex-direction: column; }
            input[type="email"], input[type="text"], select, .add-btn { flex: none; width: 100%; }
            .table-scroll { overflow-x: auto; }
            table { min-width: 480px; }
            th, td { padding: 9px 10px; font-size: 13px; }
        }
    </style>
</head>
<body>

<div class="container">
    <div class="header">
        <h1>🔐 PTPK Giriş İcazələri İdarəetmə Paneli</h1>
        <button class="logout-btn" onclick="logout()">Çıxış</button>
    </div>

    <div class="form-group">
        <input type="email" id="newEmail" placeholder="Gmail ünvanı">
        <input type="text" id="newName" placeholder="Ad, Soyad (könüllü)">
        <select id="newRole">
            <option value="user">İstifadəçi (Məktəb)</option>
            <option value="komissiya">Komissiya Üzvü</option>
            <option value="admin">Admin (İdarə)</option>
        </select>
        <button class="add-btn" id="addBtn" onclick="addEmail()">Əlavə Et</button>
    </div>

    <div class="table-scroll">
        <table id="emailsTable">
            <thead>
                <tr>
                    <th>Gmail</th>
                    <th>Ad / Soyad</th>
                    <th>Rol</th>
                    <th>Əməliyyat</th>
                </tr>
            </thead>
            <tbody id="tableBody">
                </tbody>
        </table>
    </div>
</div>

<div class="toast" id="toast"></div>

<script>
    const token = localStorage.getItem('ptpk_token');
    const role = localStorage.getItem('ptpk_role');

    if (!token || role !== 'admin') {
        alert('Bu panelə giriş icazəniz yoxdur!');
        window.location.href = '/login.html';
    }

    const ROLE_LABEL = { admin: 'admin', komissiya: 'komissiya', user: 'user' };

    function showToast(msg, isError) {
        const t = document.getElementById('toast');
        t.textContent = msg;
        t.className = 'toast' + (isError ? ' error' : '');
        t.style.display = 'block';
        setTimeout(() => { t.style.display = 'none'; }, 3500);
    }

    async function loadEmails() {
        const tbody = document.getElementById('tableBody');
        tbody.innerHTML = `<tr><td colspan="4" class="loading-row">Yüklənir...</td></tr>`;
        try {
            const res = await fetch('/api/admin/list-emails', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token })
            });
            const data = await res.json();
            if (data.status === 'forbidden') {
                showToast('Sessiyanız bitib, yenidən daxil olun', true);
                setTimeout(() => window.location.href = '/login.html', 1500);
                return;
            }
            renderTable(data.data || []);
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="4" class="empty-row">Bağlantı xətası baş verdi.</td></tr>`;
        }
    }

    function renderTable(rows) {
        const tbody = document.getElementById('tableBody');
        if (!rows.length) {
            tbody.innerHTML = `<tr><td colspan="4" class="empty-row">Heç bir qeyd tapılmadı.</td></tr>`;
            return;
        }
        tbody.innerHTML = rows.map(row => `
            <tr>
                <td>${escapeHtml(row.email)}</td>
                <td>${escapeHtml(row.name || '-')}</td>
                <td>
                    <select class="role-select" onchange="updateRole(${row.id}, this.value)">
                        <option value="user" ${row.role === 'user' ? 'selected' : ''}>İstifadəçi</option>
                        <option value="komissiya" ${row.role === 'komissiya' ? 'selected' : ''}>Komissiya</option>
                        <option value="admin" ${row.role === 'admin' ? 'selected' : ''}>Admin</option>
                    </select>
                </td>
                <td><button class="delete-btn" onclick="deleteEmail(${row.id}, '${escapeHtml(row.email)}')">Sil</button></td>
            </tr>
        `).join('');
    }

    function escapeHtml(str) {
        return String(str).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    }

    async function addEmail() {
        const emailInput = document.getElementById('newEmail');
        const nameInput = document.getElementById('newName');
        const roleSelect = document.getElementById('newRole');
        const btn = document.getElementById('addBtn');

        const email = emailInput.value.trim();
        const name = nameInput.value.trim();
        const newRole = roleSelect.value;

        if (!email) { showToast('Gmail ünvanı mütləqdir!', true); return; }

        btn.disabled = true;
        btn.textContent = 'Əlavə edilir...';

        try {
            const res = await fetch('/api/admin/add-email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, email, name, role: newRole })
            });
            const data = await res.json();
            if (data.status === 'ok') {
                showToast('✅ İstifadəçi uğurla əlavə edildi!');
                emailInput.value = '';
                nameInput.value = '';
                roleSelect.value = 'user';
                loadEmails();
            } else if (data.status === 'forbidden') {
                showToast('İcazəniz yoxdur', true);
            } else {
                showToast(data.message || 'Xəta baş verdi', true);
            }
        } catch (e) {
            showToast('Bağlantı xətası!', true);
        }

        btn.disabled = false;
        btn.textContent = 'Əlavə Et';
    }

    async function updateRole(id, newRole) {
        try {
            const res = await fetch('/api/admin/update-role', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, id, role: newRole })
            });
            const data = await res.json();
            if (data.status === 'ok') {
                showToast('✅ Rol yeniləndi');
            } else {
                showToast(data.message || 'Rol yenilənmədi', true);
                loadEmails();
            }
        } catch (e) {
            showToast('Bağlantı xətası!', true);
            loadEmails();
        }
    }

    async function deleteEmail(id, email) {
        if (!confirm(`"${email}" ünvanını siyahıdan silmək istəyirsiniz?`)) return;
        try {
            const res = await fetch('/api/admin/delete-email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, id })
            });
            const data = await res.json();
            if (data.status === 'ok') {
                showToast('✅ Silindi');
                loadEmails();
            } else {
                showToast(data.message || 'Silinmədi', true);
            }
        } catch (e) {
            showToast('Bağlantı xətası!', true);
        }
    }

    function logout() {
        localStorage.clear();
        window.location.href = '/login.html';
    }

    window.onload = loadEmails;
</script>
</body>
</html>
