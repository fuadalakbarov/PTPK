const express = require('express');
const router = express.Router();
const supabase = require('../db/supabase');
const { verifyToken } = require('../middleware/auth');

// GÖNDƏR
router.post('/', verifyToken, async (req, res) => {
  const { receiver_id, content } = req.body;
  if (!receiver_id || !content) return res.status(400).json({ error: 'Alıcı və mətn tələb olunur' });

  const { data, error } = await supabase
    .from('messages')
    .insert([{ sender_id: req.user.id, receiver_id, content }])
    .select().single();
  if (error) return res.status(400).json({ error: error.message });
  res.json(data);
});

// İKİ NƏFƏR ARASINDA YAZIŞMA TARİXÇƏSİ
router.get('/thread/:otherId', verifyToken, async (req, res) => {
  const { otherId } = req.params;
  const { data, error } = await supabase
    .from('messages')
    .select('*')
    .or(`and(sender_id.eq.${req.user.id},receiver_id.eq.${otherId}),and(sender_id.eq.${otherId},receiver_id.eq.${req.user.id})`)
    .order('created_at');
  if (error) return res.status(400).json({ error: error.message });

  // oxunmamışları oxunmuş et
  await supabase.from('messages').update({ is_read: true })
    .eq('receiver_id', req.user.id).eq('sender_id', otherId).eq('is_read', false);

  res.json(data);
});

// SON YAZIŞMALAR SİYAHISI (kimlərlə danışılıb)
router.get('/conversations', verifyToken, async (req, res) => {
  const { data: msgs, error } = await supabase
    .from('messages')
    .select('*')
    .or(`sender_id.eq.${req.user.id},receiver_id.eq.${req.user.id}`)
    .order('created_at', { ascending: false });
  if (error) return res.status(400).json({ error: error.message });

  const map = new Map();
  msgs.forEach(m => {
    const otherId = m.sender_id === req.user.id ? m.receiver_id : m.sender_id;
    if (!map.has(otherId)) {
      map.set(otherId, { other_id: otherId, last_message: m.content, last_at: m.created_at, unread: 0 });
    }
    if (m.receiver_id === req.user.id && !m.is_read) {
      map.get(otherId).unread += 1;
    }
  });
  res.json(Array.from(map.values()));
});

module.exports = router;
