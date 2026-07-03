const express = require('express');
const router = express.Router();
const supabase = require('../db/supabase');
const { verifyToken, requireAdmin } = require('../middleware/auth');
const { calcEmployeePoints } = require('./_points');

// BÜTÜN İŞÇİLƏR (admin üçün ümumi siyahı, sektor üzrə qruplaşdırılmadan)
router.get('/', verifyToken, requireAdmin, async (req, res) => {
  const { data: employees, error } = await supabase
    .from('employees')
    .select('id, full_name, position, email, role, photo_url, sector_id, is_active, phone')
    .order('full_name');
  if (error) return res.status(400).json({ error: error.message });
  res.json(employees);
});

// TƏK İŞÇİ PROFİLİ (öz tapşırıqları, balı ilə)
router.get('/:id', verifyToken, async (req, res) => {
  const { id } = req.params;
  if (req.user.role !== 'admin' && req.user.id !== id) {
    return res.status(403).json({ error: 'İcazə yoxdur' });
  }
  const { data: emp, error } = await supabase
    .from('employees')
    .select('id, full_name, position, email, role, photo_url, sector_id, phone')
    .eq('id', id).single();
  if (error) return res.status(404).json({ error: 'İşçi tapılmadı' });

  const { data: tasks } = await supabase.from('tasks').select('*').eq('employee_id', id).order('created_at', { ascending: false });

  res.json({ ...emp, tasks, stats: calcEmployeePoints(tasks || []) });
});

// İŞÇİNİ YENİLƏ (admin)
router.put('/:id', verifyToken, requireAdmin, async (req, res) => {
  const { id } = req.params;
  const { full_name, position, sector_id, photo_url, phone, is_active } = req.body;
  const { data, error } = await supabase
    .from('employees')
    .update({ full_name, position, sector_id, photo_url, phone, is_active })
    .eq('id', id).select().single();
  if (error) return res.status(400).json({ error: error.message });
  res.json(data);
});

router.delete('/:id', verifyToken, requireAdmin, async (req, res) => {
  const { id } = req.params;
  const { error } = await supabase.from('employees').update({ is_active: false }).eq('id', id);
  if (error) return res.status(400).json({ error: error.message });
  res.json({ success: true });
});

module.exports = router;
