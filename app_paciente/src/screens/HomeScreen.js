import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView, StyleSheet,
  Text, TouchableOpacity, View,
} from 'react-native';
import {
  getBuddyHistory, getDiet, getMyMetrics, getMyPatient, getTodayCheckins, logout,
  saveCheckin, sendBuddyMessage,
} from '../api';
import BuddyHome from '../buddy/BuddyHome';
import BuddyPet from '../buddy/BuddyPet';
import SkinPicker from '../buddy/SkinPicker';
import { DEFAULT_SKIN, loadSkin, saveSkin } from '../buddy/skins';

const MEALS = [
  { key: 'cafe', label: 'Café da manhã', time: '', icon: '☀️' },
  { key: 'lanche1', label: 'Lanche da manhã', time: '', icon: '🍎' },
  { key: 'almoco', label: 'Almoço', time: '', icon: '🥗' },
  { key: 'lanche2', label: 'Lanche da tarde', time: '', icon: '🍓' },
  { key: 'jantar', label: 'Jantar', time: '', icon: '🌙' },
  { key: 'pre_treino', label: 'Pré-treino', time: '', icon: '⚡' },
  { key: 'pos_treino', label: 'Pós-treino', time: '', icon: '💪' },
  { key: 'pre_atividade', label: 'Pré-atividade física', time: '', icon: '🏃' },
  { key: 'pos_atividade', label: 'Pós-atividade física', time: '', icon: '🥤' },
];

// Como o bichinho reage a cada resposta do backend.
function reactionFor(response, { missed } = {}) {
  if (response.applied_today_only) return 'happy';
  if (response.needs_nutritionist) return 'serious';
  if (missed) return 'comfort';
  if (response.awaiting_confirmation) return 'curious';
  return null;
}

export default function HomeScreen({ user, onLogout }) {
  const [patient, setPatient] = useState(null);
  const [diet, setDiet] = useState(null);
  const [mealConfigs, setMealConfigs] = useState({});
  const [mealNutrition, setMealNutrition] = useState({});
  const [metrics, setMetrics] = useState(null);
  const [checkins, setCheckins] = useState({});
  const [tab, setTab] = useState('today');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const [savingMeal, setSavingMeal] = useState('');
  const [skin, setSkin] = useState(DEFAULT_SKIN);
  const [skinPickerOpen, setSkinPickerOpen] = useState(false);
  const [reaction, setReaction] = useState(null);
  const skinOwner = user.user_id || user.email || user.name;

  function react(type, food) {
    if (type) setReaction({ type, food, key: `${type}-${Date.now()}` });
  }

  async function chooseSkin(nextSkin) {
    setSkin(nextSkin);
    setSkinPickerOpen(false);
    react('happy');
    await saveSkin(skinOwner, nextSkin.id);
  }

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const profile = await getMyPatient();
      const [dietData, metricData, checkinData, chatHistory] = await Promise.all([
        getDiet(profile.id),
        getMyMetrics(profile.id),
        getTodayCheckins(),
        getBuddyHistory(),
      ]);
      setPatient(profile);
      setDiet(dietData.today_meals || dietData.meals);
      setMealConfigs(dietData.meal_configs || {});
      setMealNutrition(dietData.today_meal_nutrition || dietData.meal_nutrition || {});
      setMetrics(metricData);
      setSkin(await loadSkin(skinOwner, metricData.level));
      setCheckins(checkinData);
      setMessages(chatHistory.length
        ? chatHistory.map(message => ({
          ...message,
          needsNutritionist: message.needs_nutritionist,
          quickReplies: message.quick_replies || [],
        }))
        : [{
          id: 'welcome', from: 'buddy',
          text: `Oi, ${user.name.split(' ')[0]}! Eu sou o Buddy 💚 Tô aqui pra deixar seu dia mais gostoso e leve. Quer trocar algum alimento ou bater um papo?`,
        }]
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  async function refreshDietAfterBuddyChange(response) {
    if (!response.applied_today_only || !patient) return;
    try {
      const updatedDiet = await getDiet(patient.id);
      setDiet(updatedDiet.today_meals || updatedDiet.meals);
      setMealConfigs(updatedDiet.meal_configs || {});
      setMealNutrition(updatedDiet.today_meal_nutrition || updatedDiet.meal_nutrition || {});
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCheckin(meal, followed) {
    setSavingMeal(meal.key);
    try {
      await saveCheckin(meal.key, followed);
      setCheckins(current => ({ ...current, [meal.key]: followed }));
      if (followed) react('eat', meal.icon);
      if (!followed) {
        setTab('buddy');
        const mealLabel = (mealConfigs[meal.key]?.label || meal.label).toLowerCase();
        const message = `Não consegui seguir o plano no ${mealLabel} hoje.`;
        setMessages(current => [...current, { id: `${Date.now()}-user`, from: 'user', text: message }]);
        setSending(true);
        try {
          const response = await sendBuddyMessage(message);
          setMessages(current => [...current, {
            id: `${Date.now()}-reply`, from: 'buddy',
            text: response.message || 'Tudo bem se hoje não saiu como planejado 💚 Vamos retomar com calma, sem compensar nem cortar alimentos.',
            needsNutritionist: response.needs_nutritionist,
            quickReplies: response.quick_replies || [],
          }]);
          react(reactionFor(response, { missed: true }));
          await refreshDietAfterBuddyChange(response);
        } catch (err) {
          setMessages(current => [...current, { id: `${Date.now()}-error`, from: 'buddy', text: `Não consegui falar com o Buddy: ${err.message}` }]);
        } finally {
          setSending(false);
        }
      }
      if (patient) {
        const updated = await getMyMetrics(patient.id);
        if (updated.level > (metrics?.level ?? 1)) react('happy', '⭐');
        setMetrics(updated);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingMeal('');
    }
  }

  async function handleSend(text) {
    if (!text || sending) return;
    setMessages(current => [...current, { id: `${Date.now()}-user`, from: 'user', text }]);
    setSending(true);
    try {
      const response = await sendBuddyMessage(text);
      setMessages(current => [...current, {
        id: `${Date.now()}-reply`, from: 'buddy',
        text: response.message || 'Estou aqui com você. Se for uma mudança importante no seu plano, vamos chamar seu nutricionista.',
        needsNutritionist: response.needs_nutritionist,
        quickReplies: response.quick_replies || [],
      }]);
      react(reactionFor(response));
      await refreshDietAfterBuddyChange(response);
    } catch (err) {
      setMessages(current => [...current, { id: `${Date.now()}-error`, from: 'buddy', text: `Ops, não consegui te ouvir agora 🙉 ${err.message}` }]);
    } finally {
      setSending(false);
    }
  }

  async function handleLogout() {
    await logout();
    onLogout();
  }

  const greetingName = user.name.split(' ')[0];
  const today = new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' });

  if (loading) {
    return <View style={styles.center}><ActivityIndicator size="large" color="#39834f" /><Text style={styles.loadingText}>Preparando seu dia...</Text></View>;
  }

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <View style={styles.topbar}>
        <View>
          <Text style={styles.brand}>nutribuddy <Text style={styles.brandLeaf}>✳</Text></Text>
          <Text style={styles.topGreeting}>Oi, {greetingName}!</Text>
        </View>
        <TouchableOpacity onPress={handleLogout} style={styles.logoutButton}><Text style={styles.logoutText}>Sair</Text></TouchableOpacity>
      </View>
      {error ? (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity onPress={loadDashboard}><Text style={styles.retryText}>Tentar novamente</Text></TouchableOpacity>
        </View>
      ) : null}
      <View style={styles.tabs}>
        <TouchableOpacity onPress={() => setTab('today')} style={[styles.tab, tab === 'today' && styles.activeTab]}>
          <Text style={[styles.tabText, tab === 'today' && styles.activeTabText]}>Meu dia</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => setTab('buddy')} style={[styles.tab, tab === 'buddy' && styles.activeTab]}>
          <Text style={[styles.tabText, tab === 'buddy' && styles.activeTabText]}>Casa do Buddy</Text>
        </TouchableOpacity>
      </View>

      {tab === 'today' ? (
        <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
          <Text style={styles.dateText}>{today}</Text>
          <View style={styles.heroCard}>
            <View style={styles.heroCopy}>
              <Text style={styles.heroEyebrow}>SEU COMPANHEIRO DE ROTINA</Text>
              <Text style={styles.heroTitle}>Um passo de cada vez.</Text>
              <Text style={styles.heroText}>Seu plano está aqui. Sem cobranças — só cuidado e constância.</Text>
            </View>
            <BuddyPet skin={skin} size={96} mood={metrics?.mood} reaction={reaction} onPress={() => setTab('buddy')} />
          </View>

          <View style={styles.statsRow}>
            <View style={styles.statCard}><Text style={styles.statValue}>{metrics?.weekly_adherence ?? 0}%</Text><Text style={styles.statLabel}>da semana</Text></View>
            <View style={styles.statCard}><Text style={styles.statValue}>🔥 {metrics?.streak ?? 0}</Text><Text style={styles.statLabel}>dias de rotina</Text></View>
            <View style={styles.statCard}><Text style={styles.statValue}>Nível {metrics?.level ?? 1}</Text><Text style={styles.statLabel}>{metrics?.xp ?? 0} pontos</Text></View>
          </View>

          <View style={styles.sectionHeading}>
            <View><Text style={styles.sectionTitle}>Seu plano de hoje</Text><Text style={styles.sectionSubtitle}>Feito com carinho pelo seu nutricionista</Text></View>
          </View>
          {MEALS.map(meal => {
            const items = diet?.[meal.key] || [];
            if (items.length === 0) return null;
            const cfg = mealConfigs[meal.key];
            const mealLabel = cfg?.label || meal.label;
            const mealTime = cfg?.time || meal.time;
            const nutrition = mealNutrition[meal.key];
            return (
              <View key={meal.key} style={styles.mealCard}>
                <View style={styles.mealHeading}>
                  <Text style={styles.mealIcon}>{meal.icon}</Text>
                  <View style={styles.mealTitleWrap}>
                    <Text style={styles.mealTitle}>{mealLabel}</Text>
                    {mealTime || (nutrition && nutrition.matched_items > 0) ? (
                      <Text style={styles.mealTime}>
                        {[mealTime, nutrition && nutrition.matched_items > 0 ? `${nutrition.kcal} kcal` : ''].filter(Boolean).join(' · ')}
                      </Text>
                    ) : null}
                  </View>
                  {checkins[meal.key] === true ? <Text style={styles.doneTag}>Feito ✓</Text> : null}
                  {checkins[meal.key] === false ? <Text style={styles.missedTag}>Buddy avisado</Text> : null}
                </View>
                {items.map(item => (
                  <Text key={item.id} style={styles.foodLine}>
                    •  {item.food} <Text style={styles.foodQty}>— {item.qty}{item.kcal != null ? ` · ${item.kcal} kcal` : ''}</Text>
                  </Text>
                ))}
                <View style={styles.mealActions}>
                  <TouchableOpacity disabled={savingMeal === meal.key} onPress={() => handleCheckin(meal, true)} style={[styles.mealAction, checkins[meal.key] === true && styles.selectedAction]}>
                    <Text style={[styles.mealActionText, checkins[meal.key] === true && styles.selectedActionText]}>{savingMeal === meal.key ? 'Salvando...' : '✓  Segui'}</Text>
                  </TouchableOpacity>
                  <TouchableOpacity disabled={savingMeal === meal.key} onPress={() => handleCheckin(meal, false)} style={styles.missedAction}>
                    <Text style={styles.missedActionText}>Não consegui</Text>
                  </TouchableOpacity>
                </View>
              </View>
            );
          })}
          <View style={styles.noteCard}><Text style={styles.noteIcon}>💚</Text><Text style={styles.noteText}>Seu Buddy oferece apoio geral. Para mudanças permanentes, sintomas ou orientações clínicas, fale com seu nutricionista.</Text></View>
        </ScrollView>
      ) : (
        <BuddyHome
          firstName={greetingName}
          skin={skin}
          level={metrics?.level ?? 1}
          mood={metrics?.mood}
          messages={messages}
          sending={sending}
          reaction={reaction}
          onSend={handleSend}
          onPetTap={() => react('tap')}
          onOpenSkins={() => setSkinPickerOpen(true)}
        />
      )}
      <SkinPicker
        visible={skinPickerOpen}
        current={skin}
        level={metrics?.level ?? 1}
        xp={metrics?.xp ?? 0}
        onSelect={chooseSkin}
        onClose={() => setSkinPickerOpen(false)}
      />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f7f2' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#f5f7f2' },
  loadingText: { color: '#718076', marginTop: 12 },
  topbar: { paddingTop: Platform.OS === 'web' ? 18 : 54, paddingHorizontal: 20, paddingBottom: 14, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#fff' },
  brand: { color: '#234b36', fontSize: 14, fontWeight: '800', letterSpacing: 0.4 },
  brandLeaf: { color: '#78aa6b' },
  topGreeting: { color: '#24352a', fontSize: 22, fontWeight: '800', marginTop: 3 },
  logoutButton: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, backgroundColor: '#f4f6f1' },
  logoutText: { color: '#657267', fontWeight: '700', fontSize: 13 },
  errorBanner: { backgroundColor: '#fff0ed', margin: 12, padding: 12, borderRadius: 12 },
  errorText: { color: '#963d30', fontSize: 13 },
  retryText: { color: '#963d30', fontWeight: '700', marginTop: 8 },
  tabs: { backgroundColor: '#fff', paddingHorizontal: 16, flexDirection: 'row', borderBottomWidth: 1, borderColor: '#e8ede6' },
  tab: { paddingVertical: 13, paddingHorizontal: 14, marginRight: 8, borderBottomWidth: 2, borderBottomColor: 'transparent' },
  activeTab: { borderBottomColor: '#39834f' },
  tabText: { color: '#7a857c', fontWeight: '600', fontSize: 13 },
  activeTabText: { color: '#39834f' },
  page: { padding: 18, paddingBottom: 36, maxWidth: 720, width: '100%', alignSelf: 'center' },
  dateText: { color: '#79847a', fontSize: 13, textTransform: 'capitalize', marginBottom: 12 },
  heroCard: { backgroundColor: '#e5f1df', borderRadius: 22, padding: 19, minHeight: 140, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', overflow: 'hidden' },
  heroCopy: { flex: 1, paddingRight: 8 },
  heroEyebrow: { fontSize: 9, color: '#547753', letterSpacing: 1.2, fontWeight: '800', marginBottom: 8 },
  heroTitle: { fontSize: 22, fontWeight: '800', color: '#294b35', marginBottom: 6 },
  heroText: { fontSize: 12, lineHeight: 18, color: '#5e7561', maxWidth: 290 },
  statsRow: { flexDirection: 'row', marginTop: 12, marginBottom: 24 },
  statCard: { flex: 1, backgroundColor: '#fff', paddingVertical: 14, paddingHorizontal: 8, borderRadius: 16, marginRight: 8, alignItems: 'center', borderWidth: 1, borderColor: '#edf0ea' },
  statValue: { color: '#2e6740', fontWeight: '800', fontSize: 17 },
  statLabel: { color: '#859087', fontSize: 10, marginTop: 5, textAlign: 'center' },
  sectionHeading: { marginBottom: 13 },
  sectionTitle: { color: '#26392e', fontSize: 19, fontWeight: '800' },
  sectionSubtitle: { color: '#839087', fontSize: 12, marginTop: 4 },
  mealCard: { backgroundColor: '#fff', borderRadius: 17, padding: 15, marginBottom: 11, borderWidth: 1, borderColor: '#e9eee7' },
  mealHeading: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  mealIcon: { fontSize: 22, marginRight: 11 },
  mealTitleWrap: { flex: 1 },
  mealTitle: { color: '#29382e', fontSize: 14, fontWeight: '700' },
  mealTime: { color: '#929c93', fontSize: 11, marginTop: 3 },
  doneTag: { backgroundColor: '#e6f4e3', color: '#39834f', paddingHorizontal: 9, paddingVertical: 5, borderRadius: 20, fontSize: 10, overflow: 'hidden', fontWeight: '700' },
  missedTag: { backgroundColor: '#fff2df', color: '#9b6b26', paddingHorizontal: 9, paddingVertical: 5, borderRadius: 20, fontSize: 10, overflow: 'hidden', fontWeight: '700' },
  foodLine: { color: '#435047', fontSize: 13, marginTop: 6, lineHeight: 19 },
  foodQty: { color: '#7e8980' },
  emptyMeal: { color: '#98a198', fontSize: 12, fontStyle: 'italic', marginVertical: 5 },
  mealActions: { flexDirection: 'row', marginTop: 13, borderTopWidth: 1, borderColor: '#f0f2ed', paddingTop: 10 },
  mealAction: { paddingVertical: 8, paddingHorizontal: 13, borderRadius: 10, backgroundColor: '#f5f8f3', marginRight: 8 },
  selectedAction: { backgroundColor: '#e5f1df' },
  mealActionText: { color: '#5b715e', fontSize: 12, fontWeight: '700' },
  selectedActionText: { color: '#39834f' },
  missedAction: { paddingVertical: 8, paddingHorizontal: 12 },
  missedActionText: { color: '#898f89', fontSize: 12 },
  noteCard: { backgroundColor: '#f0f3ed', borderRadius: 14, padding: 13, flexDirection: 'row', alignItems: 'flex-start', marginTop: 3 },
  noteIcon: { fontSize: 16, marginRight: 9 },
  noteText: { color: '#6f7d71', fontSize: 11, lineHeight: 17, flex: 1 },
});
