const express = require('express');
const router = express.Router();
const supabase = require('../db/supabase');
const { verifyToken, requireAdmin } = require('../middleware/auth');
const { calcEmployeePoints } = require('./_points');

// BÜTÜN SEKTORLAR + hər sektorun performans xülasəsi
router.get('/', verifyToken, async (req, res) => {
  const { data: sectors, error } = await supabase
    .from('sectors')
    .select('*')
    .order('sort_order');
  if (error) return res.status(400).json({ error: error.message });

  const { data: employees } = await supabase.from('employees').select('*').eq('is_active', true);
  const { data: tasks } = await supabase.from('tasks').select('*');

  const result = sectors.map(sector => {
    const sectorEmployees = employees.filter(e => e.sector_id === sector.id);
    const empWithStats = sectorEmployees.map(emp => {
      const empTasks = tasks.filter(t => t.employee_id === emp.id);
      return { ...emp, stats: calcEmployeePoints(empTasks) };
    });
    const avgPoints = empWithStats.length
      ? Math.round(empWithStats.reduce((s, e) => s + e.stats.points, 0) / empWithStats.length)
      : 0;
    const avgCompletion = empWithStats.length
      ? Math.round(empWithStats.reduce((s, e) => s + e.stats.completionRate, 0) / empWithStats.length)
      : 0;
    return {
      ...sector,
      employee_count: sectorEmployees.length,
      avg_points: avgPoints,
      avg_completion: avgCompletion,
      task_count: tasks.filter(t => sectorEmployees.some(e => e.id === t.employee_id)).length
    };
  });

  res.json(result);
});

// TƏK SEKTOR + işçilər (şəkil, bal, tamamlama %)
router.get('/:id/employees', verifyToken, async (req, res) => {
  const { id } = req.params;
  const { data: employees, error } = await supabase
    .from('employees')
    .select('*')
    .eq('sector_id', id)
    .eq('is_active', true);
  if (error) return res.status(400).json({ error: error.message });

  const { data: tasks } = await supabase.from('tasks').select('*');

  const result = employees.map(emp => {
    const empTasks = tasks.filter(t => t.employee_id === emp.id);
    const { password_hash, ...safe } = emp;
    return { ...safe, stats: calcEmployeePoints(empTasks) };
  });

  res.json(result.sort((a, b) => b.stats.points - a.stats.points));
});

// SEKTOR YARAT (admin)
router.post('/', verifyToken, requireAdmin, async (req, res) => {
  const { name, description, color, sort_order } = req.body;
  const { data, error } = await supabase
    .from('sectors')
    .insert([{ name, description, color, sort_order }])
    .select().single();
  if (error) return res.status(400).json({ error: error.message });
  res.json(data);
});

module.exports = router;
