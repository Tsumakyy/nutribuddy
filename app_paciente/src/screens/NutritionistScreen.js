import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator, Alert, KeyboardAvoidingView, Platform, ScrollView,
  StyleSheet, Text, TextInput, TouchableOpacity, View,
} from 'react-native';
import {
  addDietItem, createPatient, getBuddyRequests, getDiet, getPatients, logout, removeDietItem,
  searchFoods, updateMealConfig,
} from '../api';

const MEALS = [
  { key: 'cafe', label: 'Café da manhã', defaultTime: '', icon: '☀️' },
  { key: 'lanche1', label: 'Lanche da manhã', defaultTime: '', icon: '🍎' },
  { key: 'almoco', label: 'Almoço', defaultTime: '', icon: '🥗' },
  { key: 'lanche2', label: 'Lanche da tarde', defaultTime: '', icon: '🍓' },
  { key: 'jantar', label: 'Jantar', defaultTime: '', icon: '🌙' },
  { key: 'pre_treino', label: 'Pré-treino', defaultTime: '', icon: '⚡' },
  { key: 'pos_treino', label: 'Pós-treino', defaultTime: '', icon: '💪' },
  { key: 'pre_atividade', label: 'Pré-atividade física', defaultTime: '', icon: '🏃' },
  { key: 'pos_atividade', label: 'Pós-atividade física', defaultTime: '', icon: '🥤' },
];

const PRESET_MEAL_NAMES = [
  'Café da manhã',
  'Lanche da manhã',
  'Almoço',
  'Lanche da tarde',
  'Jantar',
  'Pré-treino',
  'Pós-treino',
  'Pré-atividade física',
  'Pós-atividade física',
];

function parseGrams(qtyText) {
  const match = String(qtyText || '').trim().match(/^(\d+(?:[.,]\d+)?)\s*(?:g|gr|gramas?)?$/i);
  if (!match) return null;
  const val = parseFloat(match[1].replace(',', '.'));
  return Number.isFinite(val) && val > 0 ? val : null;
}

function normalizeQtyForSave(qtyText) {
  const trimmed = String(qtyText || '').trim();
  if (/^\d+(?:[.,]\d+)?$/.test(trimmed)) {
    return `${trimmed.replace(',', '.')} g`;
  }
  return trimmed;
}

const EMPTY_FORM = { name: '', email: '', password: '', goal: '' };

export default function NutritionistScreen({ user, onLogout }) {
  const [patients, setPatients] = useState([]);
  const [selected, setSelected] = useState(null);
  const [diet, setDiet] = useState(null);
  const [mealConfigs, setMealConfigs] = useState({});
  const [mealNutrition, setMealNutrition] = useState({});
  const [editingMealKey, setEditingMealKey] = useState(null);
  const [mealConfigForm, setMealConfigForm] = useState({ label: '', time: '' });
  const [buddyRequests, setBuddyRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [itemForm, setItemForm] = useState({
    mealKey: 'cafe',
    mealLabel: 'Café da manhã',
    mealTime: '',
    food: '',
    qty: '',
  });
  const [foodSuggestions, setFoodSuggestions] = useState([]);
  const [foodSearchError, setFoodSearchError] = useState('');
  const [foodSearchLoading, setFoodSearchLoading] = useState(false);
  const [selectedFoodInfo, setSelectedFoodInfo] = useState(null);

  const loadPatients = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setPatients(await getPatients());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadPatients(); }, [loadPatients]);

  useEffect(() => {
    let active = true;
    const query = itemForm.food.trim();
    if (query.length < 2 || selectedFoodInfo?.name === query) {
      setFoodSuggestions([]);
      setFoodSearchError('');
      setFoodSearchLoading(false);
      return () => { active = false; };
    }

    const timeout = setTimeout(async () => {
      setFoodSearchLoading(true);
      setFoodSearchError('');
      try {
        const results = await searchFoods(query);
        if (active) setFoodSuggestions(results);
      } catch (err) {
        if (active) {
          setFoodSuggestions([]);
          setFoodSearchError(err.message);
        }
      } finally {
        if (active) setFoodSearchLoading(false);
      }
    }, 250);

    return () => {
      active = false;
      clearTimeout(timeout);
    };
  }, [itemForm.food, selectedFoodInfo]);

  useEffect(() => {
    let active = true;
    async function loadDiet() {
      if (!selected) {
        setDiet(null);
        setBuddyRequests([]);
        return;
      }
      setDiet(null);
      setBuddyRequests([]);
      setError('');
      try {
        const [result, requests] = await Promise.all([
          getDiet(selected.id),
          getBuddyRequests(selected.id),
        ]);
        if (active) {
          setDiet(result.meals);
          setMealConfigs(result.meal_configs || {});
          setMealNutrition(result.meal_nutrition || {});
          setEditingMealKey(null);
          setBuddyRequests(requests);
        }
      } catch (err) {
        if (active) setError(err.message);
      }
    }
    loadDiet();
    return () => { active = false; };
  }, [selected]);

  async function handleCreatePatient() {
    if (!form.name.trim() || !form.email.trim() || form.password.length < 6) {
      Alert.alert('Confira os dados', 'Informe nome, e-mail e uma senha de pelo menos 6 caracteres.');
      return;
    }
    setSaving(true);
    try {
      const created = await createPatient({ ...form, name: form.name.trim(), email: form.email.trim() });
      setForm(EMPTY_FORM);
      setShowForm(false);
      setPatients(current => [...current, created]);
      setSelected(created);
    } catch (err) {
      Alert.alert('Não foi possível cadastrar', err.message);
    } finally {
      setSaving(false);
    }
  }

  async function refreshDiet() {
    if (!selected) return;
    const result = await getDiet(selected.id);
    setDiet(result.meals);
    setMealConfigs(result.meal_configs || {});
    setMealNutrition(result.meal_nutrition || {});
  }

  function handleOpenMealConfig(meal) {
    const cfg = mealConfigs[meal.key];
    setEditingMealKey(meal.key);
    setMealConfigForm({
      label: cfg?.label || meal.label,
      time: cfg?.time || meal.defaultTime,
    });
  }

  async function handleSaveMealConfig(mealKey) {
    if (!selected || !mealConfigForm.label.trim()) {
      Alert.alert('Preencha os campos', 'Informe o nome da refeição.');
      return;
    }
    setSaving(true);
    try {
      await updateMealConfig(selected.id, mealKey, {
        label: mealConfigForm.label.trim(),
        time: mealConfigForm.time.trim(),
      });
      setEditingMealKey(null);
      await refreshDiet();
    } catch (err) {
      Alert.alert('Não foi possível salvar', err.message);
    } finally {
      setSaving(false);
    }
  }

  function selectMealForForm(meal) {
    const cfg = mealConfigs[meal.key];
    setItemForm(current => ({
      ...current,
      mealKey: meal.key,
      mealLabel: cfg?.label || meal.label,
      mealTime: cfg?.time || '',
    }));
  }

  async function handleAddItem() {
    if (!selected || !itemForm.food.trim() || !itemForm.qty.trim()) {
      Alert.alert('Preencha os campos', 'Informe o alimento e a quantidade.');
      return;
    }
    setSaving(true);
    try {
      const targetMeal = MEALS.find(m => m.key === itemForm.mealKey);
      const currentCfg = mealConfigs[itemForm.mealKey];
      const nextLabel = (itemForm.mealLabel || targetMeal?.label || '').trim();
      const nextTime = (itemForm.mealTime || '').trim();
      if (
        nextLabel &&
        (nextLabel !== (currentCfg?.label || targetMeal?.label) || nextTime !== (currentCfg?.time || ''))
      ) {
        await updateMealConfig(selected.id, itemForm.mealKey, {
          label: nextLabel,
          time: nextTime,
        });
      }
      await addDietItem(selected.id, itemForm.mealKey, {
        food: itemForm.food.trim(),
        qty: normalizeQtyForSave(itemForm.qty),
      });
      setItemForm(current => ({ ...current, food: '', qty: '' }));
      setSelectedFoodInfo(null);
      await refreshDiet();
    } catch (err) {
      Alert.alert('Não foi possível salvar', err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleRemoveItem(mealKey, itemId) {
    try {
      await removeDietItem(selected.id, mealKey, itemId);
      await refreshDiet();
    } catch (err) {
      Alert.alert('Não foi possível remover', err.message);
    }
  }

  async function handleLogout() {
    await logout();
    onLogout();
  }

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={styles.topbar}>
        <View>
          <Text style={styles.brand}>nutribuddy <Text style={styles.brandLeaf}>✳</Text></Text>
          <Text style={styles.topGreeting}>Olá, {user.name.split(' ')[0]}</Text>
        </View>
        <TouchableOpacity onPress={handleLogout} style={styles.logoutButton}><Text style={styles.logoutText}>Sair</Text></TouchableOpacity>
      </View>
      <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
        <View style={styles.hero}>
          <Text style={styles.heroEyebrow}>PAINEL PROFISSIONAL</Text>
          <Text style={styles.heroTitle}>Acompanhamento com cuidado.</Text>
          <Text style={styles.heroText}>Organize seus pacientes e mantenha os planos alimentares sempre à mão.</Text>
        </View>

        {error ? <View style={styles.errorBanner}><Text style={styles.errorText}>{error}</Text><TouchableOpacity onPress={selected ? refreshDiet : loadPatients}><Text style={styles.retryText}>Tentar novamente</Text></TouchableOpacity></View> : null}

        <View style={styles.sectionHeading}>
          <View><Text style={styles.sectionTitle}>Seus pacientes</Text><Text style={styles.sectionSubtitle}>{patients.length} {patients.length === 1 ? 'pessoa acompanhada' : 'pessoas acompanhadas'}</Text></View>
          <TouchableOpacity style={styles.primaryButtonSmall} onPress={() => { setSelected(null); setShowForm(!showForm); }}>
            <Text style={styles.primaryButtonText}>{showForm ? 'Fechar' : '+ Novo'}</Text>
          </TouchableOpacity>
        </View>

        {showForm ? (
          <View style={styles.formCard}>
            <Text style={styles.cardTitle}>Cadastrar paciente</Text>
            <Text style={styles.formHint}>O paciente usará estes dados para entrar no app.</Text>
            <TextInput style={styles.input} placeholder="Nome completo" value={form.name} onChangeText={name => setForm(current => ({ ...current, name }))} />
            <TextInput style={styles.input} placeholder="E-mail" value={form.email} onChangeText={email => setForm(current => ({ ...current, email }))} autoCapitalize="none" keyboardType="email-address" />
            <TextInput style={styles.input} placeholder="Senha temporária (mínimo 6 caracteres)" value={form.password} onChangeText={password => setForm(current => ({ ...current, password }))} secureTextEntry />
            <TextInput style={styles.input} placeholder="Objetivo (opcional)" value={form.goal} onChangeText={goal => setForm(current => ({ ...current, goal }))} />
            <TouchableOpacity style={styles.primaryButton} onPress={handleCreatePatient} disabled={saving}>
              <Text style={styles.primaryButtonText}>{saving ? 'Salvando...' : 'Cadastrar paciente'}</Text>
            </TouchableOpacity>
          </View>
        ) : null}

        {loading ? <ActivityIndicator color="#39834f" style={styles.loader} /> : null}
        {!loading && patients.length === 0 && !showForm ? (
          <View style={styles.emptyCard}><Text style={styles.emptyIcon}>🌱</Text><Text style={styles.cardTitle}>Sua lista começa aqui</Text><Text style={styles.emptyText}>Cadastre seu primeiro paciente para montar e compartilhar o plano alimentar.</Text></View>
        ) : null}

        <View style={styles.patientList}>
          {patients.map(patient => (
            <TouchableOpacity key={patient.id} onPress={() => { setShowForm(false); setSelected(patient); }} style={[styles.patientCard, selected?.id === patient.id && styles.selectedPatient]}>
              <View style={styles.avatar}><Text style={styles.avatarText}>{patient.name.slice(0, 1).toUpperCase()}</Text></View>
              <View style={styles.patientInfo}><Text style={styles.patientName}>{patient.name}</Text><Text style={styles.patientEmail}>{patient.email}</Text>{patient.goal ? <Text style={styles.patientGoal}>{patient.goal}</Text> : null}</View>
              <Text style={styles.chevron}>›</Text>
            </TouchableOpacity>
          ))}
        </View>

        {selected ? (
          <View style={styles.dietSection}>
            <View style={styles.dietHeader}>
              <Text style={styles.sectionTitle}>Plano alimentar</Text>
              <Text style={styles.dietFor}>Para {selected.name}</Text>
            </View>
            {buddyRequests.length > 0 ? (
              <View style={styles.requestCard}>
                <Text style={styles.requestTitle}>O Buddy pediu seu acompanhamento</Text>
                <Text style={styles.requestHint}>Revise estas dúvidas do paciente na próxima conversa.</Text>
                {buddyRequests.map(request => (
                  <View key={request.id} style={styles.requestItem}>
                    <Text style={styles.requestMessage}>{request.message}</Text>
                    <Text style={styles.requestDate}>{new Date(request.created_at).toLocaleString('pt-BR')}</Text>
                  </View>
                ))}
              </View>
            ) : null}
            {diet ? MEALS.map(meal => {
              const cfg = mealConfigs[meal.key];
              const mealLabel = cfg?.label || meal.label;
              const mealTime = cfg?.time || meal.defaultTime;
              const nutrition = mealNutrition[meal.key];
              const items = diet[meal.key] || [];
              const isEditing = editingMealKey === meal.key;

              return (
                <View key={meal.key} style={styles.mealCard}>
                  <View style={styles.mealHeader}>
                    <Text style={styles.mealIcon}>{meal.icon}</Text>
                    <View style={styles.mealHeaderCopy}>
                      <Text style={styles.mealTitle}>
                        {mealLabel}{mealTime ? <Text style={styles.mealTimeTag}> · {mealTime}</Text> : <Text style={styles.mealTimeTag}> · Horário não definido</Text>}
                      </Text>
                      {nutrition && nutrition.matched_items > 0 ? (
                        <Text style={styles.mealKcalText}>
                          {nutrition.kcal} kcal · P {nutrition.protein_g} g · C {nutrition.carbs_g} g · G {nutrition.fat_g} g
                          {!nutrition.complete ? ' (parcial)' : ''}
                        </Text>
                      ) : null}
                    </View>
                    <TouchableOpacity onPress={() => isEditing ? setEditingMealKey(null) : handleOpenMealConfig(meal)}>
                      <Text style={styles.editMealLink}>{isEditing ? 'Cancelar' : 'Editar nome/horário'}</Text>
                    </TouchableOpacity>
                  </View>

                  {isEditing ? (
                    <View style={styles.mealConfigBox}>
                      <Text style={styles.mealConfigHint}>Escolha um nome pré-selecionado ou personalize:</Text>
                      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.mealPicker}>
                        {PRESET_MEAL_NAMES.map(preset => (
                          <TouchableOpacity
                            key={preset}
                            onPress={() => setMealConfigForm(c => ({ ...c, label: preset }))}
                            style={[styles.mealChip, mealConfigForm.label === preset && styles.mealChipActive]}
                          >
                            <Text style={[styles.mealChipText, mealConfigForm.label === preset && styles.mealChipTextActive]}>{preset}</Text>
                          </TouchableOpacity>
                        ))}
                      </ScrollView>
                      <View style={styles.mealConfigRow}>
                        <TextInput
                          style={[styles.input, styles.mealConfigLabelInput]}
                          placeholder="Nome da refeição"
                          value={mealConfigForm.label}
                          onChangeText={label => setMealConfigForm(c => ({ ...c, label }))}
                        />
                        <TextInput
                          style={[styles.input, styles.mealConfigTimeInput]}
                          placeholder="Horário (ex.: 08:00)"
                          value={mealConfigForm.time}
                          onChangeText={time => setMealConfigForm(c => ({ ...c, time }))}
                        />
                      </View>
                      <TouchableOpacity style={styles.primaryButtonSmall} onPress={() => handleSaveMealConfig(meal.key)} disabled={saving}>
                        <Text style={styles.primaryButtonText}>{saving ? 'Salvando...' : 'Salvar nome e horário'}</Text>
                      </TouchableOpacity>
                    </View>
                  ) : null}

                  {items.length === 0 ? <Text style={styles.emptyMeal}>Nenhum alimento adicionado.</Text> : items.map(item => (
                    <View key={item.id} style={styles.foodRow}>
                      <Text style={styles.foodText}>
                        {item.food} <Text style={styles.foodQty}>· {item.qty}{item.kcal != null ? ` · ${item.kcal} kcal` : ''}</Text>
                      </Text>
                      <TouchableOpacity onPress={() => handleRemoveItem(meal.key, item.id)}><Text style={styles.removeText}>Remover</Text></TouchableOpacity>
                    </View>
                  ))}
                </View>
              );
            }) : <ActivityIndicator color="#39834f" style={styles.loader} />}

            <View style={styles.formCard}>
              <Text style={styles.cardTitle}>Adicionar alimento</Text>
              <Text style={styles.formHint}>Digite o nome do alimento (ex.: arroz) para escolher da lista TACO e informe a quantidade em gramas para calcular calorias automaticamente.</Text>
              <View style={styles.mealPickerGrid}>
                {MEALS.map(meal => {
                  const mealLabel = mealConfigs[meal.key]?.label || meal.label;
                  return (
                    <TouchableOpacity key={meal.key} onPress={() => selectMealForForm(meal)} style={[styles.mealChip, styles.mealChipGrid, itemForm.mealKey === meal.key && styles.mealChipActive]}>
                      <Text style={[styles.mealChipText, itemForm.mealKey === meal.key && styles.mealChipTextActive]}>{meal.icon} {mealLabel}</Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
              <View style={styles.mealConfigRow}>
                <TextInput
                  style={[styles.input, styles.mealConfigLabelInput]}
                  placeholder="Nome da refeição"
                  value={itemForm.mealLabel}
                  onChangeText={mealLabel => setItemForm(current => ({ ...current, mealLabel }))}
                />
                <TextInput
                  style={[styles.input, styles.mealConfigTimeInput]}
                  placeholder="Horário (ex.: 07:30)"
                  value={itemForm.mealTime}
                  onChangeText={mealTime => setItemForm(current => ({ ...current, mealTime }))}
                />
              </View>
              <TextInput
                style={styles.input}
                placeholder="Alimento (ex.: arroz)"
                value={itemForm.food}
                onChangeText={food => {
                  setItemForm(current => ({ ...current, food }));
                  setSelectedFoodInfo(null);
                }}
              />
              {foodSearchLoading ? <ActivityIndicator color="#39834f" size="small" style={styles.foodSearchLoader} /> : null}
              {foodSearchError ? <Text style={styles.foodSearchError}>Busca nutricional indisponível: {foodSearchError}</Text> : null}
              {foodSuggestions.map(food => (
                <TouchableOpacity
                  key={food.name}
                  style={styles.foodSuggestion}
                  onPress={() => {
                    setItemForm(current => ({ ...current, food: food.name }));
                    setSelectedFoodInfo(food);
                    setFoodSuggestions([]);
                  }}
                >
                  <Text style={styles.foodSuggestionName}>{food.name}</Text>
                  <Text style={styles.foodSuggestionDetails}>
                    {food.category} · {food.kcal} kcal · P {food.protein_g} g · C {food.carbs_g} g · G {food.fat_g} g / 100 g
                  </Text>
                </TouchableOpacity>
              ))}
              {selectedFoodInfo ? (
                <Text style={styles.nutritionInfo}>
                  {selectedFoodInfo.source} · {selectedFoodInfo.kcal} kcal / 100 g (P {selectedFoodInfo.protein_g}g · C {selectedFoodInfo.carbs_g}g · G {selectedFoodInfo.fat_g}g)
                </Text>
              ) : (
                <Text style={styles.nutritionInfo}>
                  Digite pelo menos 2 letras para ver opções da tabela TACO. Alimentos fora do catálogo continuam aceitando cadastro manual.
                </Text>
              )}
              <TextInput
                style={styles.input}
                placeholder="Quantidade em gramas (ex.: 150 ou 150 g)"
                value={itemForm.qty}
                onChangeText={qty => setItemForm(current => ({ ...current, qty }))}
              />
              {(() => {
                const grams = parseGrams(itemForm.qty);
                if (!selectedFoodInfo || !grams) return null;
                const factor = grams / 100;
                return (
                  <Text style={styles.previewKcal}>
                    Porção ({grams} g): {(selectedFoodInfo.kcal * factor).toFixed(1)} kcal · P {(selectedFoodInfo.protein_g * factor).toFixed(1)} g · C {(selectedFoodInfo.carbs_g * factor).toFixed(1)} g · G {(selectedFoodInfo.fat_g * factor).toFixed(1)} g
                  </Text>
                );
              })()}
              <TouchableOpacity style={styles.primaryButton} onPress={handleAddItem} disabled={saving}>
                <Text style={styles.primaryButtonText}>{saving ? 'Salvando...' : 'Adicionar ao plano'}</Text>
              </TouchableOpacity>
            </View>
          </View>
        ) : null}
        <Text style={styles.footerNote}>As orientações do plano são definidas pelo profissional responsável.</Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f7f2' },
  topbar: { paddingTop: Platform.OS === 'web' ? 18 : 54, paddingHorizontal: 20, paddingBottom: 14, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#fff' },
  brand: { color: '#234b36', fontSize: 14, fontWeight: '800', letterSpacing: 0.4 },
  brandLeaf: { color: '#78aa6b' },
  topGreeting: { color: '#24352a', fontSize: 22, fontWeight: '800', marginTop: 3 },
  logoutButton: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, backgroundColor: '#f4f6f1' },
  logoutText: { color: '#657267', fontWeight: '700', fontSize: 13 },
  page: { padding: 18, paddingBottom: 40, maxWidth: 760, width: '100%', alignSelf: 'center' },
  hero: { backgroundColor: '#e5f1df', borderRadius: 22, padding: 21, marginBottom: 24 },
  heroEyebrow: { fontSize: 9, color: '#547753', letterSpacing: 1.2, fontWeight: '800', marginBottom: 8 },
  heroTitle: { color: '#294b35', fontSize: 21, fontWeight: '800' },
  heroText: { color: '#627665', fontSize: 13, lineHeight: 19, marginTop: 7 },
  errorBanner: { backgroundColor: '#fff0ed', marginBottom: 14, padding: 12, borderRadius: 12 },
  errorText: { color: '#963d30', fontSize: 13 },
  retryText: { color: '#963d30', fontWeight: '700', marginTop: 8 },
  sectionHeading: { marginBottom: 13, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  sectionTitle: { color: '#26392e', fontSize: 19, fontWeight: '800' },
  sectionSubtitle: { color: '#839087', fontSize: 12, marginTop: 4 },
  primaryButtonSmall: { backgroundColor: '#39834f', borderRadius: 11, paddingHorizontal: 14, paddingVertical: 10 },
  primaryButton: { backgroundColor: '#39834f', borderRadius: 12, padding: 14, alignItems: 'center', marginTop: 3 },
  primaryButtonText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  patientList: { marginBottom: 20 },
  patientCard: { backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: '#e9eee7', padding: 13, flexDirection: 'row', alignItems: 'center', marginBottom: 9 },
  selectedPatient: { borderColor: '#72a67a', backgroundColor: '#f6faf3' },
  avatar: { width: 42, height: 42, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: '#e5f1df', marginRight: 12 },
  avatarText: { color: '#39834f', fontWeight: '800', fontSize: 17 },
  patientInfo: { flex: 1 },
  patientName: { color: '#2b3a30', fontSize: 14, fontWeight: '700' },
  patientEmail: { color: '#879188', fontSize: 11, marginTop: 3 },
  patientGoal: { color: '#648066', fontSize: 11, marginTop: 4 },
  chevron: { color: '#a3aca3', fontSize: 26, marginLeft: 8 },
  formCard: { backgroundColor: '#fff', borderRadius: 18, padding: 17, marginBottom: 14, borderWidth: 1, borderColor: '#e9eee7' },
  cardTitle: { color: '#2b3a30', fontWeight: '800', fontSize: 16 },
  formHint: { color: '#829087', fontSize: 11, lineHeight: 16, marginTop: 5, marginBottom: 13 },
  input: { backgroundColor: '#f7f9f5', borderRadius: 11, padding: 13, marginBottom: 9, borderWidth: 1, borderColor: '#e8ede6', color: '#29382e', fontSize: 13 },
  foodSearchLoader: { marginVertical: 6 },
  foodSearchError: { color: '#963d30', fontSize: 11, marginBottom: 9 },
  foodSuggestion: { backgroundColor: '#f2f7ef', borderRadius: 10, padding: 11, marginBottom: 7 },
  foodSuggestionName: { color: '#294333', fontWeight: '700', fontSize: 12 },
  foodSuggestionDetails: { color: '#718076', fontSize: 10, lineHeight: 15, marginTop: 4 },
  nutritionInfo: { color: '#718076', fontSize: 10, lineHeight: 15, marginBottom: 9 },
  loader: { marginVertical: 22 },
  emptyCard: { backgroundColor: '#fff', borderRadius: 18, padding: 22, alignItems: 'center', borderWidth: 1, borderColor: '#e9eee7', marginBottom: 18 },
  emptyIcon: { fontSize: 34, marginBottom: 10 },
  emptyText: { color: '#849087', textAlign: 'center', lineHeight: 19, fontSize: 12, marginTop: 7, maxWidth: 300 },
  dietSection: { marginTop: 3 },
  dietHeader: { marginBottom: 13 },
  dietFor: { color: '#839087', fontSize: 12, marginTop: 4 },
  requestCard: { backgroundColor: '#fff7e9', borderRadius: 16, padding: 14, marginBottom: 12, borderWidth: 1, borderColor: '#f0dfc1' },
  requestTitle: { color: '#805b25', fontWeight: '800', fontSize: 14 },
  requestHint: { color: '#927747', fontSize: 11, marginTop: 5, marginBottom: 7 },
  requestItem: { borderTopWidth: 1, borderColor: '#f0e5d2', paddingTop: 8, marginTop: 6 },
  requestMessage: { color: '#594b37', fontSize: 12, lineHeight: 18 },
  requestDate: { color: '#9a8b72', fontSize: 10, marginTop: 4 },
  mealCard: { backgroundColor: '#fff', borderRadius: 16, padding: 14, marginBottom: 9, borderWidth: 1, borderColor: '#e9eee7' },
  mealHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 7 },
  mealHeaderCopy: { flex: 1 },
  mealIcon: { fontSize: 19, marginRight: 9 },
  mealTitle: { color: '#2c3b31', fontWeight: '700', fontSize: 13 },
  mealTimeTag: { color: '#748176', fontWeight: '600', fontSize: 12 },
  mealKcalText: { color: '#39834f', fontSize: 11, fontWeight: '700', marginTop: 2 },
  editMealLink: { color: '#39834f', fontSize: 11, fontWeight: '700', paddingLeft: 8 },
  mealConfigBox: { backgroundColor: '#f7f9f5', borderRadius: 12, padding: 11, marginBottom: 9, borderWidth: 1, borderColor: '#e8ede6' },
  mealConfigHint: { color: '#718076', fontSize: 11, marginBottom: 7 },
  mealConfigRow: { flexDirection: 'row', gap: 8 },
  mealConfigLabelInput: { flex: 2 },
  mealConfigTimeInput: { flex: 1 },
  previewKcal: { color: '#39834f', fontSize: 11, fontWeight: '700', marginBottom: 9, marginTop: -3 },
  emptyMeal: { color: '#98a198', fontSize: 11, fontStyle: 'italic', paddingVertical: 5 },
  foodRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderTopWidth: 1, borderColor: '#f0f2ed', paddingVertical: 9 },
  foodText: { color: '#48564b', fontSize: 12, flex: 1 },
  foodQty: { color: '#839087' },
  removeText: { color: '#b55b4b', fontSize: 11, fontWeight: '600', paddingLeft: 10 },
  mealPicker: { marginBottom: 11 },
  mealPickerGrid: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 8 },
  mealChip: { paddingHorizontal: 11, paddingVertical: 8, borderRadius: 20, backgroundColor: '#f3f6f0', marginRight: 7 },
  mealChipGrid: { marginBottom: 7 },
  mealChipActive: { backgroundColor: '#e2f0df' },
  mealChipText: { color: '#748176', fontSize: 11, fontWeight: '600' },
  mealChipTextActive: { color: '#39834f' },
  footerNote: { color: '#929c93', textAlign: 'center', fontSize: 10, marginTop: 8 },
});
