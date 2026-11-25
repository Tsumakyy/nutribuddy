import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { login, registerNutritionist } from '../api';

export default function LoginScreen({ onLogin, notice }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit() {
    try {
      setLoading(true);
      const user = isRegistering
        ? await registerNutritionist(name.trim(), email.trim(), password)
        : await login(email.trim(), password);
      onLogin(user);
    } catch (err) {
      Alert.alert('Erro', err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View style={styles.brandMark}><Text style={styles.brandEmoji}>🌱</Text></View>
        <Text style={styles.title}>NutriBuddy</Text>
        <Text style={styles.subtitle}>Cuidado leve, acompanhamento de verdade.</Text>
        {notice ? <Text style={styles.notice}>{notice}</Text> : null}

        <View style={styles.form}>
          <Text style={styles.formTitle}>{isRegistering ? 'Crie seu acesso profissional' : 'Que bom ter você por aqui'}</Text>
          {isRegistering && (
            <TextInput
              style={styles.input}
              placeholder="Seu nome"
              value={name}
              onChangeText={setName}
              autoCapitalize="words"
            />
          )}
          <TextInput
            style={styles.input}
            placeholder="E-mail"
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
          />
          <TextInput
            style={styles.input}
            placeholder="Senha (mínimo 6 caracteres)"
            secureTextEntry
            value={password}
            onChangeText={setPassword}
          />

          <TouchableOpacity style={styles.button} onPress={handleSubmit} disabled={loading}>
            <Text style={styles.buttonText}>
              {loading ? 'Aguarde...' : isRegistering ? 'Criar conta de nutricionista' : 'Entrar'}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => setIsRegistering(!isRegistering)} style={styles.switchButton}>
            <Text style={styles.switchText}>
              {isRegistering ? 'Já tenho uma conta. Entrar' : 'Sou nutricionista e quero me cadastrar'}
            </Text>
          </TouchableOpacity>
        </View>
        <Text style={styles.footnote}>Acesso para nutricionistas e pacientes convidados.</Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f7f2' },
  content: { flexGrow: 1, justifyContent: 'center', padding: 24, maxWidth: 520, width: '100%', alignSelf: 'center' },
  brandMark: { width: 72, height: 72, borderRadius: 24, backgroundColor: '#e4f2df', alignSelf: 'center', alignItems: 'center', justifyContent: 'center', marginBottom: 12 },
  brandEmoji: { fontSize: 36 },
  title: { fontSize: 34, fontWeight: '800', color: '#234b36', textAlign: 'center', letterSpacing: -1 },
  subtitle: { fontSize: 15, color: '#718076', textAlign: 'center', marginTop: 8, marginBottom: 32 },
  notice: { color: '#8a6122', backgroundColor: '#fff2df', padding: 12, borderRadius: 12, marginBottom: 14, fontSize: 12 },
  form: { backgroundColor: '#fff', borderRadius: 24, padding: 22, borderWidth: 1, borderColor: '#e8ede6' },
  formTitle: { fontSize: 18, fontWeight: '700', color: '#26392e', marginBottom: 18 },
  input: { backgroundColor: '#f8faf7', borderRadius: 13, padding: 15, marginBottom: 12, borderWidth: 1, borderColor: '#e6ebe3', color: '#26392e' },
  button: { backgroundColor: '#39834f', borderRadius: 13, padding: 16, marginTop: 4 },
  buttonText: { color: '#fff', fontWeight: '700', textAlign: 'center', fontSize: 15 },
  switchButton: { padding: 14, alignItems: 'center' },
  switchText: { color: '#39834f', fontWeight: '700', textAlign: 'center' },
  footnote: { color: '#869188', fontSize: 12, textAlign: 'center', marginTop: 22 },
});