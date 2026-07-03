// Avtomatik bal hesablama: tapşırıq tamamlanma faizi + vaxtında olma + keyfiyyət balı əsasında

function calcEmployeePoints(tasks) {
  const total = tasks.length;
  if (total === 0) {
    return { points: 0, completionRate: 0, completedCount: 0, totalCount: 0, overdueCount: 0 };
  }

  const completed = tasks.filter(t => t.status === 'completed');
  const overdue = tasks.filter(t => t.status === 'overdue');
  const completionRate = Math.round((completed.length / total) * 100);

  let points = 0;
  completed.forEach(t => {
    const onTime = !t.due_date || !t.completed_at || new Date(t.completed_at) <= new Date(t.due_date + 'T23:59:59');
    let base = onTime ? 10 : 6; // vaxtında = 10, gecikmiş tamamlama = 6
    if (t.quality_score != null) {
      base = base * (t.quality_score / 100); // keyfiyyət balı varsa, ona görə çəkilir
    }
    points += base;
  });
  points -= overdue.length * 3; // açıq qalıb vaxtı keçən tapşırıqlar bal azaldır

  return {
    points: Math.max(0, Math.round(points)),
    completionRate,
    completedCount: completed.length,
    totalCount: total,
    overdueCount: overdue.length
  };
}

module.exports = { calcEmployeePoints };
