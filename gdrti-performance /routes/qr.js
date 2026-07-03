const express = require('express');
const router = express.Router();
const jwt = require('jsonwebtoken');
const supabase = require('../db/supabase');
require('dotenv').config();

const EXPIRY_MS = 3 * 60 * 1000; // QR kod 3 dəqiqə etibarlıdır

// 1) KOMPÜTER: yeni QR sessiya yaradır
router.post('/create', async (req, res) => {
  const { data, error } = await supabase
    .from('qr_sessions')
    .insert([{ status: 'pending' }])
    .select().single();
  if (error) return res.status(400).json({ error: error.message });
  res.json({ session_id: data.id });
});

// 2) KOMPÜTER: statusu pollayır (2 saniyədə bir)
router.get('/status/:id', async (req, res) => {
  const { data, error } = await supabase
    .from('qr_sessions')
    .select('*')
    .eq('id', req.params.id)
    .single();
  if (error || !data) return res.status(404).json({ error: 'Sessiya tapılmadı' });

  const age = Date.now() - new Date(data.created_at).getTime();
  if (data.status === 'pending' && age > EXPIRY_MS) {
    return res.json({ status: 'expired' });
  }
  res.json({ status: data.status, token: data.token, user: data.user_payload });
});

// 3) TELEFON: artıq öz app tokeni ilə daxil olub, QR sessiyanı bu hesaba bağlayır
router.post('/confirm', async (req, res) => {
  const { session_id, token } = req.body;
  if (!session_id || !token) return res.status(400).json({ error: 'session_id və token tələb olunur' });

  let payload;
  try { payload = jwt.verify(token, process.env.JWT_SECRET); }
  catch { return res.status(401).json({ error: 'Token etibarsızdır, yenidən daxil olun' }); }

  const { data: session } = await supabase.from('qr_sessions').select('*').eq('id', session_id).single();
  if (!session) return res.status(404).json({ error: 'Sessiya tapılmadı' });
  const age = Date.now() - new Date(session.created_at).getTime();
  if (session.status !== 'pending' || age > EXPIRY_MS) {
    return res.status(410).json({ error: 'QR kodun vaxtı bitib, kompüterdə yenisini yaradın' });
  }

  const { data: emp } = await supabase
    .from('employees')
    .select('id, full_name, role, sector_id, position, photo_url')
    .eq('id', payload.id).single();
  if (!emp) return res.status(404).json({ error: 'İstifadəçi tapılmadı' });

  const { error } = await supabase
    .from('qr_sessions')
    .update({ status: 'confirmed', token, user_payload: emp })
    .eq('id', session_id)
    .eq('status', 'pending');
  if (error) return res.status(400).json({ error: error.message });

  res.json({ success: true });
});

module.exports = router;
