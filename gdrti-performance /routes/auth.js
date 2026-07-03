const express = require('express');
const router = express.Router();
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const supabase = require('../db/supabase');
require('dotenv').config();

// LOGIN
router.post('/login', async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) return res.status(400).json({ error: 'Email və şifrə tələb olunur' });

  const { data: employee, error } = await supabase
    .from('employees')
    .select('*')
    .eq('email', email.toLowerCase().trim())
    .eq('is_active', true)
    .single();

  if (error || !employee) return res.status(401).json({ error: 'Email və ya şifrə yanlışdır' });

  const match = await bcrypt.compare(password, employee.password_hash);
  if (!match) return res.status(401).json({ error: 'Email və ya şifrə yanlışdır' });

  const token = jwt.sign(
    { id: employee.id, role: employee.role, sector_id: employee.sector_id, full_name: employee.full_name },
    process.env.JWT_SECRET,
    { expiresIn: '7d' }
  );

  res.json({
    token,
    user: {
      id: employee.id,
      full_name: employee.full_name,
      role: employee.role,
      sector_id: employee.sector_id,
      position: employee.position,
      photo_url: employee.photo_url
    }
  });
});

// ADMIN YENİ İŞÇİ YARADIR (registration - qorunmalıdır, sonradan admin token tələb oluna bilər)
router.post('/register', async (req, res) => {
  const { full_name, email, password, position, sector_id, role, photo_url, phone } = req.body;
  if (!full_name || !email || !password) return res.status(400).json({ error: 'Ad, email və şifrə tələb olunur' });

  const password_hash = await bcrypt.hash(password, 10);

  const { data, error } = await supabase
    .from('employees')
    .insert([{
      full_name, email: email.toLowerCase().trim(), password_hash,
      position, sector_id, phone,
      role: role === 'admin' ? 'admin' : 'employee',
      photo_url: photo_url || null
    }])
    .select()
    .single();

  if (error) return res.status(400).json({ error: error.message });
  delete data.password_hash;
  res.json(data);
});

// GOOGLE İLƏ GİRİŞ / QEYDİYYAT (işçilər üçün)
// Frontend Supabase Auth vasitəsilə Google ilə daxil olur, bura Supabase access_token göndərir.
// Biz onu Supabase-də doğrulayırıq, employees cədvəlində uyğun sətri tapır ya yaradırıq.
router.post('/google', async (req, res) => {
  const { access_token } = req.body;
  if (!access_token) return res.status(400).json({ error: 'access_token tələb olunur' });

  const { data: googleUser, error: verifyError } = await supabase.auth.getUser(access_token);
  if (verifyError || !googleUser?.user) return res.status(401).json({ error: 'Google girişi doğrulanmadı' });

  const gUser = googleUser.user;
  const email = (gUser.email || '').toLowerCase().trim();
  if (!email) return res.status(400).json({ error: 'Google hesabında email tapılmadı' });

  const fullName = gUser.user_metadata?.full_name || gUser.user_metadata?.name || email.split('@')[0];
  const avatarUrl = gUser.user_metadata?.avatar_url || gUser.user_metadata?.picture || null;

  let { data: employee } = await supabase
    .from('employees')
    .select('*')
    .eq('email', email)
    .single();

  if (!employee) {
    // Yeni işçi — sektor hələ təyin olunmayıb, admin təsdiqləməlidir
    const { data: created, error: insertError } = await supabase
      .from('employees')
      .insert([{
        full_name: fullName, email, password_hash: null,
        role: 'employee', sector_id: null, photo_url: avatarUrl,
        auth_provider: 'google', is_active: true
      }])
      .select().single();
    if (insertError) return res.status(400).json({ error: insertError.message });
    employee = created;
  } else if (!employee.is_active) {
    return res.status(403).json({ error: 'Bu hesab deaktiv edilib. Admin ilə əlaqə saxlayın.' });
  } else if (!employee.photo_url && avatarUrl) {
    // profil şəkli yoxdursa, Google avatarını götürək
    await supabase.from('employees').update({ photo_url: avatarUrl }).eq('id', employee.id);
    employee.photo_url = avatarUrl;
  }

  const token = jwt.sign(
    { id: employee.id, role: employee.role, sector_id: employee.sector_id, full_name: employee.full_name },
    process.env.JWT_SECRET,
    { expiresIn: '7d' }
  );

  res.json({
    token,
    user: {
      id: employee.id,
      full_name: employee.full_name,
      role: employee.role,
      sector_id: employee.sector_id,
      position: employee.position,
      photo_url: employee.photo_url,
      pending: !employee.sector_id // sektor təyin olunmayıbsa, gözləmə vəziyyətindədir
    }
  });
});

module.exports = router;
