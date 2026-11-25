import React, { useEffect, useRef, useState } from 'react';
import { Animated, Easing, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { DEFAULT_SKIN } from './skins';

const NATIVE = Platform.OS !== 'web';

// Partículas que sobem do bichinho em cada reação.
const PARTICLES = {
  happy: ['🎉', '✨', '💚'],
  eat: ['😋', '✨'],
  comfort: ['💚', '🤗'],
  serious: ['🩺'],
  curious: ['❓'],
  tap: ['😆', '💛'],
};
const MOOD_BADGE = { fome: '🍽️', feliz: '✨', tranquilo: '😌', triste: '🫂' };

function Particle({ emoji, delay, offsetX, onDone }) {
  const progress = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.timing(progress, {
      toValue: 1, duration: 1200, delay, easing: Easing.out(Easing.quad), useNativeDriver: NATIVE,
    }).start(onDone);
  }, []);
  return (
    <Animated.Text
      style={[styles.particle, {
        opacity: progress.interpolate({ inputRange: [0, 0.2, 0.8, 1], outputRange: [0, 1, 1, 0] }),
        transform: [
          { translateX: offsetX },
          { translateY: progress.interpolate({ inputRange: [0, 1], outputRange: [0, -90] }) },
          { scale: progress.interpolate({ inputRange: [0, 0.3, 1], outputRange: [0.4, 1.2, 1] }) },
        ],
      }]}
    >
      {emoji}
    </Animated.Text>
  );
}

/**
 * Bichinho do Buddy.
 * - respira e flutua parado;
 * - balança enquanto `talking` é verdadeiro;
 * - `reaction` ({ type, key, food }) dispara uma animação única: happy, eat, comfort, serious, curious, tap.
 */
export default function BuddyPet({ skin = DEFAULT_SKIN, size = 150, mood, talking, reaction, onPress }) {
  const breathe = useRef(new Animated.Value(0)).current;
  const talk = useRef(new Animated.Value(0)).current;
  const jump = useRef(new Animated.Value(0)).current;
  const squash = useRef(new Animated.Value(0)).current;
  const shake = useRef(new Animated.Value(0)).current;
  const [particles, setParticles] = useState([]);

  // Respiração contínua
  useEffect(() => {
    const loop = Animated.loop(Animated.sequence([
      Animated.timing(breathe, { toValue: 1, duration: 1600, easing: Easing.inOut(Easing.sin), useNativeDriver: NATIVE }),
      Animated.timing(breathe, { toValue: 0, duration: 1600, easing: Easing.inOut(Easing.sin), useNativeDriver: NATIVE }),
    ]));
    loop.start();
    return () => loop.stop();
  }, [breathe]);

  // "Falando": balancinho rápido
  useEffect(() => {
    if (!talking) {
      talk.stopAnimation();
      Animated.timing(talk, { toValue: 0, duration: 120, useNativeDriver: NATIVE }).start();
      return undefined;
    }
    const loop = Animated.loop(Animated.sequence([
      Animated.timing(talk, { toValue: 1, duration: 170, useNativeDriver: NATIVE }),
      Animated.timing(talk, { toValue: -1, duration: 170, useNativeDriver: NATIVE }),
    ]));
    loop.start();
    return () => loop.stop();
  }, [talking, talk]);

  // Reações pontuais
  useEffect(() => {
    if (!reaction?.type) return;
    const hop = (height, times) => Animated.sequence(Array.from({ length: times }, () => Animated.sequence([
      Animated.timing(jump, { toValue: -height, duration: 220, easing: Easing.out(Easing.quad), useNativeDriver: NATIVE }),
      Animated.timing(jump, { toValue: 0, duration: 260, easing: Easing.bounce, useNativeDriver: NATIVE }),
    ])));
    const squish = times => Animated.sequence(Array.from({ length: times }, () => Animated.sequence([
      Animated.timing(squash, { toValue: 1, duration: 110, useNativeDriver: NATIVE }),
      Animated.timing(squash, { toValue: 0, duration: 140, useNativeDriver: NATIVE }),
    ])));
    const wiggle = Animated.sequence([-1, 1, -1, 1, 0].map(value => (
      Animated.timing(shake, { toValue: value, duration: 70, useNativeDriver: NATIVE })
    )));
    const animations = {
      happy: hop(34, 2),
      eat: squish(3),
      comfort: Animated.sequence([squish(1), hop(10, 1)]),
      serious: wiggle,
      curious: hop(14, 1),
      tap: Animated.parallel([squish(1), hop(18, 1)]),
    };
    animations[reaction.type]?.start();

    const emojis = [...(reaction.food ? [reaction.food] : []), ...(PARTICLES[reaction.type] || [])];
    setParticles(current => [
      ...current,
      ...emojis.map((emoji, index) => ({
        id: `${reaction.key}-${index}`, emoji, delay: index * 180, offsetX: (index - (emojis.length - 1) / 2) * 34,
      })),
    ]);
  }, [reaction?.key]);

  const scaleX = Animated.add(
    breathe.interpolate({ inputRange: [0, 1], outputRange: [1, 1.025] }),
    squash.interpolate({ inputRange: [0, 1], outputRange: [0, 0.12] }),
  );
  const scaleY = Animated.add(
    breathe.interpolate({ inputRange: [0, 1], outputRange: [1, 0.975] }),
    squash.interpolate({ inputRange: [0, 1], outputRange: [0, -0.14] }),
  );
  const translateY = Animated.add(
    jump,
    Animated.add(
      breathe.interpolate({ inputRange: [0, 1], outputRange: [0, -4] }),
      talk.interpolate({ inputRange: [-1, 1], outputRange: [0, -5] }),
    ),
  );
  const rotate = Animated.add(talk, shake).interpolate({ inputRange: [-2, 2], outputRange: ['-12deg', '12deg'] });
  const shadowScale = jump.interpolate({ inputRange: [-40, 0], outputRange: [0.6, 1], extrapolate: 'clamp' });

  return (
    <Pressable onPress={onPress} style={[styles.wrap, { width: size * 1.3, height: size * 1.25 }]}
      accessibilityRole="button" accessibilityLabel={`Buddy, o ${skin.name.toLowerCase()}`}>
      <Animated.View style={[styles.shadow, {
        width: size * 0.7, height: size * 0.1, borderRadius: size, transform: [{ scaleX: shadowScale }],
      }]} />
      <Animated.Image
        source={skin.image}
        style={{ width: size, height: size, transform: [{ translateY }, { rotate }, { scaleX }, { scaleY }] }}
        resizeMode="contain"
      />
      {mood && MOOD_BADGE[mood] ? (
        <View style={[styles.badge, { right: size * 0.08, top: size * 0.06 }]}>
          <Text style={styles.badgeText}>{MOOD_BADGE[mood]}</Text>
        </View>
      ) : null}
      <View pointerEvents="none" style={[styles.particles, { top: size * 0.15 }]}>
        {particles.map(particle => (
          <Particle key={particle.id} {...particle}
            onDone={() => setParticles(current => current.filter(item => item.id !== particle.id))} />
        ))}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', justifyContent: 'flex-end' },
  shadow: { position: 'absolute', bottom: 4, backgroundColor: 'rgba(30, 50, 35, 0.14)' },
  badge: {
    position: 'absolute', backgroundColor: '#fff', borderRadius: 16, width: 32, height: 32,
    alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: '#e6ebe3',
  },
  badgeText: { fontSize: 16 },
  particles: { position: 'absolute', left: 0, right: 0, alignItems: 'center' },
  particle: { position: 'absolute', fontSize: 26 },
});
