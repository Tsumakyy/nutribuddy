import React from 'react';
import { Image, Modal, Pressable, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SKINS, isUnlocked } from './skins';

export default function SkinPicker({ visible, current, level, xp, onSelect, onClose }) {
  const nextLevelXp = (level || 1) * 100;
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={() => {}}>
          <View style={styles.handle} />
          <Text style={styles.title}>Visual do Buddy 🎨</Text>
          <Text style={styles.subtitle}>
            Siga seu plano pra ganhar pontos e liberar novos amigos! Faltam {Math.max(0, nextLevelXp - (xp || 0))} pontos pro nível {(level || 1) + 1}.
          </Text>
          <ScrollView contentContainerStyle={styles.grid}>
            {SKINS.map(skin => {
              const unlocked = isUnlocked(skin, level);
              const selected = skin.id === current?.id;
              return (
                <TouchableOpacity
                  key={skin.id}
                  disabled={!unlocked}
                  onPress={() => onSelect(skin)}
                  style={[styles.card, { backgroundColor: skin.tint }, selected && styles.selected]}
                  accessibilityLabel={unlocked ? `Escolher ${skin.name}` : `${skin.name}, libera no nível ${skin.level}`}
                >
                  <Image source={skin.image} style={[styles.image, !unlocked && styles.locked]} />
                  <Text style={styles.name}>{skin.name}</Text>
                  <Text style={[styles.status, selected && styles.statusSelected]}>
                    {selected ? 'Usando ✓' : unlocked ? 'Disponível' : `🔒 Nível ${skin.level}`}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>
          <TouchableOpacity style={styles.close} onPress={onClose}>
            <Text style={styles.closeText}>Fechar</Text>
          </TouchableOpacity>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(20, 35, 25, 0.35)', justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: '#fff', borderTopLeftRadius: 26, borderTopRightRadius: 26, padding: 20, paddingBottom: 28,
    maxHeight: '82%', width: '100%', maxWidth: 720, alignSelf: 'center',
  },
  handle: { width: 42, height: 5, borderRadius: 3, backgroundColor: '#dde3da', alignSelf: 'center', marginBottom: 14 },
  title: { color: '#24392c', fontSize: 19, fontWeight: '800' },
  subtitle: { color: '#78867b', fontSize: 12, lineHeight: 18, marginTop: 5, marginBottom: 14 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' },
  card: {
    width: '31%', borderRadius: 18, alignItems: 'center', paddingVertical: 12, marginBottom: 10,
    borderWidth: 2, borderColor: 'transparent',
  },
  selected: { borderColor: '#39834f' },
  image: { width: 64, height: 64 },
  locked: { opacity: 0.28 },
  name: { color: '#2d3f33', fontWeight: '700', fontSize: 13, marginTop: 6 },
  status: { color: '#7d887f', fontSize: 10, marginTop: 3 },
  statusSelected: { color: '#39834f', fontWeight: '700' },
  close: { marginTop: 6, alignSelf: 'center', paddingVertical: 10, paddingHorizontal: 26, borderRadius: 20, backgroundColor: '#f1f5ee' },
  closeText: { color: '#456a4e', fontWeight: '700' },
});
