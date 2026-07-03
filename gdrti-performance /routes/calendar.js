const express = require('express');
const router = express.Router();
const supabase = require('../db/supabase');
const { verifyToken, requireAdmin } = require('../middleware/auth');

// AY ÜZRƏ HADİSƏLƏR (admin hamısını görür, işçi öz + öz sektorunu)
router.get('/', verifyToken, async (req, res) => {
  const { from, to } = req.query; // YYYY-MM-DD
  let query = supabase.from('calendar_events').select('*');
  if (from) query = query.gte('event_date', from);
  if (to) query = query.lte('event_date', to);

  const { data, error } = await query.order('event_date');
  if (error) return res.status(400).json({ error: error.message });

  if (req.user.role === 'admin') return res.json(data);

  const filtered = data.filter(e =>
    e.employee_id === req.user.id ||
    e.sector_id === req.user.sector_id ||
    (!e.employee_id && !e.sector_id)
  );
  res.json(filtered);
});

// HADİSƏ YARAT
router.post('/', verifyToken, async (req, res) => {
  const { title, description, event_date, event_time, type, employee_id, sector_id } = req.body;
  if (!title || !event_date) return res.status(400).json({ error: 'Başlıq və tarix tələb olunur' });

  if (req.user.role !== 'admin' && employee_id && employee_id !== req.user.id) {
    return res.status(403).json({ error: 'İcazə yoxdur' });
  }

  const { data, error } = await supabase
    .from('calendar_events')
    .insert([{
      title, description, event_date, event_time, type: type || 'event',
      employee_id: employee_id || (req.user.role !== 'admin' ? req.user.id : null),
      sector_id: sector_id || null,
      created_by: req.user.id
    }])
    .select().single();
  if (error) return res.status(400).json({ error: error.message });
  res.json(data);
});

router.delete('/:id', verifyToken, async (req, res) => {
  const { data: ev } = await supabase.from('calendar_events').select('*').eq('id', req.params.id).single();
  if (!ev) return res.status(404).json({ error: 'Tapılmadı' });
  if (req.user.role !== 'admin' && ev.created_by !== req.user.id) {
    return res.status(403).json({ error: 'İcazə yoxdur' });
  }
  const { error } = await supabase.from('calendar_events').delete().eq('id', req.params.id);
  if (error) return res.status(400).json({ error: error.message });
  res.json({ success: true });
});

module.exports = router;
