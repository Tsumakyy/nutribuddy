import React, { useMemo, useState } from 'react';
import {
  Keyboard, Modal, Platform, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View,
} from 'react-native';
import BuddyPet from './BuddyPet';
import SpeechBubble from './SpeechBubble';

// Dicas curtas para quando o paciente toca no bichinho (sem chamar o backend).
const TAP_LINES = [
  'Hihi, cócegas não! 😆 Já tomou água agora há pouco? 💧',
  'Sabia que mastigar devagar ajuda a perceber a saciedade? Bora com calma 😌',
  'Psiu! Se quiser variar alguma refeição, é só me falar tipo "quero trocar o arroz do almoço" 😉',
  'Um prato colorido costuma ter mais variedade de nutrientes 🌈',
  'Tô torcendo por você hoje! Um passo de cada vez 💚',
  'Dica do Buddy: deixar frutas lavadas à vista facilita na hora do lanche 🍎',
];
const SUGGESTIONS = ['Quero trocar um alimento', 'Não consegui seguir o almoço', 'Me dá uma dica'];

function scene() {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 12) return { bg: '#fff6dc', ground: '#f1e6bf', sky: '☀️', label: 'Bom dia' };
  if (hour >= 12 && hour < 18) return { bg: '#e6f3df', ground: '#d3e8c8', sky: '⛅', label: 'Boa tarde' };
  return { bg: '#e2e7f6', ground: '#cfd8ee', sky: '🌙', label: 'Boa noite' };
}

export default function BuddyHome({
  firstName, skin, level, mood, messages, sending, reaction, onSend, onPetTap, onOpenSkins,
}) {
  const [input, setInput] = useState('');
  const [historyOpen, setHistoryOpen] = useState(false);
  const [typing, setTyping] = useState(false);
  const [tapLine, setTapLine] = useState(null);
  const sky = useMemo(scene, []);

  const lastBuddy = [...messages].reverse().find(message => message.from === 'buddy');
  const lastMessage = messages[messages.length - 1];
  const lastUser = lastMessage?.from === 'user' ? lastMessage : null;
  const bubble = tapLine || lastBuddy;
  const quickReplies = !sending && !tapLine && lastMessage?.from === 'buddy'
    ? (lastMessage.quickReplies?.length ? lastMessage.quickReplies : messages.length <= 1 ? SUGGESTIONS : [])
    : [];

  function send(text) {
    const clean = (text ?? input).trim();
    if (!clean || sending) return;
    if (text === undefined) setInput('');
    setTapLine(null);
    Keyboard.dismiss();
    onSend(clean);
  }

  function tapPet() {
    if (sending) return;
    const line = TAP_LINES[Math.floor(Math.random() * TAP_LINES.length)];
    setTapLine({ id: `tap-${Date.now()}`, text: line });
    onPetTap?.();
  }

  return (
    <View style={styles.container}>
      <View style={[styles.stage, { backgroundColor: sky.bg }]}>
        <View style={styles.stageHeader}>
          <View style={styles.chip}><Text style={styles.chipText}>{sky.sky} {sky.label}, {firstName}!</Text></View>
          <View style={styles.headerActions}>
            <TouchableOpacity style={styles.chip} onPress={() => setHistoryOpen(true)}>
              <Text style={styles.chipText}>💬 Conversa</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.chip, styles.chipAccent]} onPress={onOpenSkins}>
              <Text style={[styles.chipText, styles.chipAccentText]}>🎨 Nível {level}</Text>
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.bubbleArea}>
          {bubble || sending ? (
            <SpeechBubble
              messageKey={sending ? 'thinking' : bubble.id}
              text={sending ? '' : bubble.text}
              thinking={sending}
              note={!tapLine && bubble?.needsNutritionist ? '💬 Vale conversar sobre isso com seu nutricionista.' : null}
              onTypingChange={setTyping}
            />
          ) : null}
        </View>

        <View style={styles.petArea}>
          <View style={[styles.ground, { backgroundColor: sky.ground }]} />
          <BuddyPet skin={skin} size={150} mood={mood} talking={typing || sending} reaction={reaction} onPress={tapPet} />
          <Text style={styles.petName}>Buddy · {skin.name}</Text>
        </View>

        {lastUser && sending ? <Text style={styles.youSaid} numberOfLines={1}>Você: {lastUser.text}</Text> : null}
        {quickReplies.length ? (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.quickReplies}
            keyboardShouldPersistTaps="handled">
            {quickReplies.map(reply => (
              <TouchableOpacity key={reply} style={styles.quickReply} onPress={() => send(reply)}>
                <Text style={styles.quickReplyText}>{reply}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        ) : <View style={styles.quickRepliesSpacer} />}
      </View>

      <View style={styles.disclaimer}>
        <Text style={styles.disclaimerText}>Trocas valem só para hoje e mantêm calorias e macros. O plano do seu nutricionista continua igual.</Text>
      </View>
      <View style={[styles.inputRow, Platform.OS !== 'web' && styles.inputRowSafeBottom]}>
        <TextInput
          style={styles.input} placeholder={`Fala com o Buddy...`} placeholderTextColor="#929b92"
          value={input} onChangeText={setInput} onSubmitEditing={() => send()} returnKeyType="send" editable={!sending}
        />
        <TouchableOpacity style={[styles.sendButton, sending && styles.disabled]} onPress={() => send()} disabled={sending}>
          <Text style={styles.sendText}>Enviar</Text>
        </TouchableOpacity>
      </View>

      <Modal visible={historyOpen} animationType="slide" onRequestClose={() => setHistoryOpen(false)}>
        <View style={styles.historyContainer}>
          <View style={styles.historyHeader}>
            <Text style={styles.historyTitle}>Conversa de hoje</Text>
            <TouchableOpacity onPress={() => setHistoryOpen(false)} style={styles.historyClose}>
              <Text style={styles.historyCloseText}>Fechar</Text>
            </TouchableOpacity>
          </View>
          <ScrollView contentContainerStyle={styles.historyList}>
            {messages.map(message => (
              <View key={message.id} style={[styles.historyBubble, message.from === 'buddy' ? styles.historyBuddy : styles.historyUser]}>
                <Text style={[styles.historyText, message.from === 'user' && styles.historyUserText]}>{message.text}</Text>
              </View>
            ))}
          </ScrollView>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, width: '100%', maxWidth: 720, alignSelf: 'center' },
  stage: { flex: 1, paddingTop: 12, overflow: 'hidden' },
  stageHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 14, marginBottom: 10 },
  headerActions: { flexDirection: 'row' },
  chip: { backgroundColor: 'rgba(255,255,255,0.8)', borderRadius: 16, paddingHorizontal: 11, paddingVertical: 6, marginLeft: 6 },
  chipText: { color: '#3f5446', fontSize: 11, fontWeight: '700' },
  chipAccent: { backgroundColor: '#39834f' },
  chipAccentText: { color: '#fff' },
  bubbleArea: { flexShrink: 1, justifyContent: 'flex-end', minHeight: 60 },
  petArea: { alignItems: 'center', marginTop: 2 },
  ground: { position: 'absolute', bottom: 12, width: '140%', height: 70, borderTopLeftRadius: 400, borderTopRightRadius: 400 },
  petName: { color: '#5b6f60', fontSize: 11, fontWeight: '700', marginTop: -2, marginBottom: 4 },
  youSaid: { color: '#6f7d72', fontSize: 11, textAlign: 'center', paddingHorizontal: 30, marginBottom: 4 },
  quickReplies: { paddingHorizontal: 14, paddingBottom: 12, paddingTop: 4 },
  quickRepliesSpacer: { height: 12 },
  quickReply: {
    borderWidth: 1, borderColor: '#39834f', backgroundColor: '#fff', borderRadius: 18,
    paddingHorizontal: 13, paddingVertical: 8, marginRight: 7,
  },
  quickReplyText: { color: '#39834f', fontSize: 12, fontWeight: '700' },
  disclaimer: { paddingHorizontal: 14, paddingVertical: 6, backgroundColor: '#f5f7f2' },
  disclaimerText: { color: '#8c968d', fontSize: 10, textAlign: 'center' },
  inputRow: { flexDirection: 'row', padding: 11, borderTopWidth: 1, borderColor: '#e8ede6', backgroundColor: '#fff', alignItems: 'center' },
  inputRowSafeBottom: { paddingBottom: Platform.OS === 'ios' ? 28 : 18 },
  input: { flex: 1, backgroundColor: '#f5f7f2', borderRadius: 22, paddingHorizontal: 16, paddingVertical: 12, marginRight: 8, color: '#26392e', fontSize: 13 },
  sendButton: { backgroundColor: '#39834f', borderRadius: 20, paddingHorizontal: 17, paddingVertical: 12 },
  disabled: { opacity: 0.6 },
  sendText: { color: '#fff', fontSize: 12, fontWeight: '700' },
  historyContainer: { flex: 1, backgroundColor: '#f5f7f2', paddingTop: Platform.OS === 'web' ? 10 : 50 },
  historyHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 18, paddingBottom: 10 },
  historyTitle: { color: '#26392e', fontSize: 18, fontWeight: '800' },
  historyClose: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 18, backgroundColor: '#e8efe4' },
  historyCloseText: { color: '#456a4e', fontWeight: '700' },
  historyList: { padding: 16, maxWidth: 720, width: '100%', alignSelf: 'center' },
  historyBubble: { maxWidth: '85%', padding: 12, borderRadius: 16, marginBottom: 9 },
  historyBuddy: { backgroundColor: '#fff', alignSelf: 'flex-start', borderWidth: 1, borderColor: '#e9eee7' },
  historyUser: { backgroundColor: '#39834f', alignSelf: 'flex-end' },
  historyText: { color: '#39473d', fontSize: 13, lineHeight: 19 },
  historyUserText: { color: '#fff' },
});
