import React, { useEffect, useRef, useState } from 'react';
import { Animated, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

const NATIVE = Platform.OS !== 'web';

function ThinkingDots() {
  const dots = [useRef(new Animated.Value(0)).current, useRef(new Animated.Value(0)).current, useRef(new Animated.Value(0)).current];
  useEffect(() => {
    const loops = dots.map((dot, index) => Animated.loop(Animated.sequence([
      Animated.delay(index * 140),
      Animated.timing(dot, { toValue: 1, duration: 280, useNativeDriver: NATIVE }),
      Animated.timing(dot, { toValue: 0, duration: 280, useNativeDriver: NATIVE }),
      Animated.delay((2 - index) * 140),
    ])));
    loops.forEach(loop => loop.start());
    return () => loops.forEach(loop => loop.stop());
  }, []);
  return (
    <View style={styles.dots}>
      {dots.map((dot, index) => (
        <Animated.View key={index} style={[styles.dot, {
          transform: [{ translateY: dot.interpolate({ inputRange: [0, 1], outputRange: [0, -5] }) }],
        }]} />
      ))}
    </View>
  );
}

/**
 * Balão de fala do bichinho. O texto aparece aos poucos (efeito "falando");
 * tocar no balão mostra tudo de uma vez.
 */
export default function SpeechBubble({ messageKey, text, thinking, note, onTypingChange }) {
  const [shown, setShown] = useState(text || '');
  const timer = useRef(null);

  useEffect(() => {
    clearInterval(timer.current);
    if (!text) {
      setShown('');
      return undefined;
    }
    // Termina em ~1,6 s independentemente do tamanho da mensagem.
    const step = Math.max(1, Math.ceil(text.length / 70));
    let position = 0;
    setShown('');
    onTypingChange?.(true);
    timer.current = setInterval(() => {
      position = Math.min(text.length, position + step);
      setShown(text.slice(0, position));
      if (position >= text.length) {
        clearInterval(timer.current);
        onTypingChange?.(false);
      }
    }, 22);
    return () => clearInterval(timer.current);
  }, [messageKey]);

  function finish() {
    clearInterval(timer.current);
    setShown(text || '');
    onTypingChange?.(false);
  }

  return (
    <View style={styles.wrap}>
      <Pressable onPress={finish} style={styles.bubble}>
        {thinking ? <ThinkingDots /> : (
          <ScrollView style={styles.scroll} nestedScrollEnabled showsVerticalScrollIndicator={false}>
            <Text style={styles.text}>{shown}</Text>
            {note && shown.length === (text || '').length ? <Text style={styles.note}>{note}</Text> : null}
          </ScrollView>
        )}
      </Pressable>
      <View style={styles.tail} />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', width: '100%', paddingHorizontal: 16 },
  bubble: {
    backgroundColor: '#fff', borderRadius: 22, paddingVertical: 13, paddingHorizontal: 16, width: '100%',
    maxWidth: 520, borderWidth: 1, borderColor: '#e4eadf',
    shadowColor: '#1d3324', shadowOpacity: 0.08, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 3,
  },
  scroll: { maxHeight: 230 },
  text: { color: '#33443a', fontSize: 14, lineHeight: 20 },
  note: { color: '#8a6122', fontSize: 11, lineHeight: 16, marginTop: 8 },
  tail: {
    width: 18, height: 18, backgroundColor: '#fff', transform: [{ rotate: '45deg' }], marginTop: -10,
    borderRightWidth: 1, borderBottomWidth: 1, borderColor: '#e4eadf',
  },
  dots: { flexDirection: 'row', justifyContent: 'center', paddingVertical: 6 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#9bb59f', marginHorizontal: 4 },
});
