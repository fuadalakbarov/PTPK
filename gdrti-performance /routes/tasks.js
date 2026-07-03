const express = require('express');
const router = express.Router();
const supabase = require('../db/supabase');
const { verifyToken, requireAdmin } = require('../middleware/auth');

// ADMIN: TAPŞIRIQ TƏYİN ET
router.post('/', verifyToken, requireAdmin, async (req, res) => {
  const { employee_id, title, description, due_date } = req.body;
  if (!employee_id || !title) return res.status(400).json({ error: 'İşçi və başlıq tələb olunur' });

  const { data, error } = await supabase
    .from('tasks')
    .insert([{ employee_id, assigned_by: req.user.id, title, description, due_date, status: 'pending' }])
    .select().single();
  if (error) return res.status(400).json({ error: error.message });
  res.json(data);
});

// İŞÇİ: ÖZ TAPŞIRIQLARI
router.get('/mine', verifyToken, async (req, res) => {
  const { data, error } = await supabase
    .from('tasks').select('*').eq('employee_id', req.user.id).order('created_at', { ascending: false });
  if (error) return res.status(400).json({ error: error.message });
  res.json(data);
});

// STATUS DƏYİŞ (işçi öz tapşırığını yeniləyə bilər, admin hamısını)
router.patch('/:id/status', verifyToken, async (req, res) => {
  const { id } = req.params;
  const { status } = req.body;
  const allowed = ['pending', 'in_progress', 'completed', 'overdue', 'cancelled'];
  if (!allowed.includes(status)) return res.status(400).json({ error: 'Yanlış status' });

  const { data: task } = await supabase.from('tasks').select('*').eq('id', id).single();
  if (!task) return res.status(404).json({ error: 'Tapşırıq tapılmadı' });
  if (req.user.role !== 'admin' && task.employee_id !== req.user.id) {
    return res.status(403).json({ error: 'İcazə yoxdur' });
  }

  const update = { status };
  if (status === 'completed') update.completed_at = new Date().toISOString();

  const { data, error } = await supabase.from('tasks').update(update).eq('id', id).select().single();
  if (error) return res.status(400).json({ error: error.message });
  res.json(data);
});

// ADMIN: KEYFİYYƏT BALI VER
router.patch('/:id/quality', verifyToken, requireAdmin, async (req, res) => {
  const { id } = req.params;
  const { quality_score } = req.body;
  if (quality_score < 0 || quality_score > 100) return res.status(400).json({ error: '0-100 arası olmalıdır' });

  const { data, error } = await supabase.from('tasks').update({ quality_score }).eq('id', id).select().single();
  if (error) return res.status(400).json({ error: error.message });
  res.json(data);
});

router.delete('/:id', verifyToken, requireAdmin, async (req, res) => {
  const { error } = await supabase.from('tasks').delete().eq('id', req.params.id);
  if (error) return res.status(400).json({ error: error.message });
  res.json({ success: true });
});

module.exports = router;
