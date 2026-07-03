const API = '/api';

function getToken(){ return localStorage.getItem('token'); }
function getUser(){ try{ return JSON.parse(localStorage.getItem('user')); }catch{ return null; } }
function logout(){ localStorage.removeItem('token'); localStorage.removeItem('user'); location.href='/index.html'; }

async function apiCall(path, method='GET', body=null){
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers['Authorization'] = 'Bearer ' + token;
  const res = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : null });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Xəta baş verdi');
  return data;
}

function requireAuth(){
  if (!getToken()) { location.href = '/index.html'; return null; }
  return getUser();
}

function initials(name){
  if(!name) return '?';
  return name.split(' ').map(p=>p[0]).slice(0,2).join('').toUpperCase();
}

function timeAgo(dateStr){
  const d = new Date(dateStr);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return 'indicə';
  if (diff < 3600) return Math.floor(diff/60) + ' dəq əvvəl';
  if (diff < 86400) return Math.floor(diff/3600) + ' saat əvvəl';
  return d.toLocaleDateString('az-AZ');
}

const STATUS_LABELS = {
  pending: 'Gözləyir', in_progress: 'İcrada', completed: 'Tamamlandı',
  overdue: 'Gecikib', cancelled: 'Ləğv edilib'
};
