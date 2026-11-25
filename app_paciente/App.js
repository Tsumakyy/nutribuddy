import React, { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import LoginScreen from './src/screens/LoginScreen';
import HomeScreen from './src/screens/HomeScreen';
import NutritionistScreen from './src/screens/NutritionistScreen';
import { restoreSession } from './src/api';

export default function App() {
  const [user, setUser] = useState(null);
  const [restoring, setRestoring] = useState(true);
  const [sessionError, setSessionError] = useState('');

  useEffect(() => {
    let active = true;
    restoreSession()
      .then(savedUser => {
        if (active) setUser(savedUser);
      })
      .catch(error => {
        if (active) setSessionError(`Não foi possível restaurar sua sessão: ${error.message}`);
      })
      .finally(() => {
        if (active) setRestoring(false);
      });

    return () => { active = false; };
  }, []);

  if (restoring) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" color="#39834f" />
        <Text style={styles.loadingText}>Abrindo o NutriBuddy...</Text>
      </View>
    );
  }

  if (!user) return <LoginScreen onLogin={setUser} notice={sessionError} />;

  if (user.role === 'nutritionist') {
    return <NutritionistScreen user={user} onLogout={() => setUser(null)} />;
  }

  return <HomeScreen user={user} onLogout={() => setUser(null)} />;
}

const styles = StyleSheet.create({
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#f5f7f2' },
  loadingText: { marginTop: 12, color: '#718076' },
});