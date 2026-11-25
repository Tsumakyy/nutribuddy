import AsyncStorage from '@react-native-async-storage/async-storage';

export const API_URL = (process.env.EXPO_PUBLIC_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

async function saveSession(data) {
  await AsyncStorage.setItem('@token', data.access_token);
  await AsyncStorage.setItem('@user', JSON.stringify(data));
  return data;
}

async function request(path, options = {}) {
  const token = await AsyncStorage.getItem('@token');
  const headers = { ...options.headers };
  if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new Error(`Não foi possível conectar à API em ${API_URL}. Confira se o backend está em execução.`);
  }

  if (!response.ok) {
    let message = `Erro ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep the HTTP status when the server does not return JSON.
    }
    throw new Error(message);
  }

  if (response.status === 204) return null;
  return response.json();
}

export async function login(email, password) {
  const formData = new URLSearchParams({ username: email, password });
  return saveSession(await request('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData.toString(),
  }));
}

export async function registerNutritionist(name, email, password) {
  return saveSession(await request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password, role: 'nutritionist' }),
  }));
}

export async function logout() {
  await AsyncStorage.multiRemove(['@token', '@user']);
}

export async function restoreSession() {
  const [token, storedUser] = await Promise.all([
    AsyncStorage.getItem('@token'),
    AsyncStorage.getItem('@user'),
  ]);
  if (!token || !storedUser) return null;

  const user = JSON.parse(storedUser);
  if (!user || !['nutritionist', 'patient'].includes(user.role) || !user.name) {
    throw new Error('Os dados salvos da sessão estão inválidos. Entre novamente.');
  }
  return user;
}

export async function getPatients() {
  return request('/patients');
}

export async function getMyPatient() {
  return request('/patients/me');
}

export async function createPatient(patient) {
  return request('/patients', { method: 'POST', body: JSON.stringify(patient) });
}

export async function getDiet(patientId) {
  return request(`/patients/${patientId}/diet`);
}

export async function searchFoods(query) {
  return request(`/foods/search?q=${encodeURIComponent(query)}`);
}

export async function getBuddyRequests(patientId) {
  return request(`/patients/${patientId}/buddy/requests`);
}

export async function addDietItem(patientId, mealKey, item) {
  return request(`/patients/${patientId}/diet/${mealKey}`, {
    method: 'POST',
    body: JSON.stringify(item),
  });
}

export async function removeDietItem(patientId, mealKey, itemId) {
  return request(`/patients/${patientId}/diet/${mealKey}/${itemId}`, { method: 'DELETE' });
}

export async function updateMealConfig(patientId, mealKey, config) {
  return request(`/patients/${patientId}/diet/${mealKey}/config`, {
    method: 'PUT',
    body: JSON.stringify(config),
  });
}

export async function getTodayCheckins() {
  return request('/checkins/today');
}

export async function saveCheckin(mealKey, followed) {
  return request('/checkins', {
    method: 'POST',
    body: JSON.stringify({ meal_key: mealKey, followed }),
  });
}

export async function getMyMetrics(patientId) {
  return request(`/metrics/${patientId}`);
}

export async function sendBuddyMessage(text) {
  return request('/buddy/chat', {
    method: 'POST',
    body: JSON.stringify({ content: text }),
  });
}

export async function getBuddyHistory() {
  return request('/buddy/history');
}