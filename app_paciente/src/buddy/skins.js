import AsyncStorage from '@react-native-async-storage/async-storage';

// Imagens: Microsoft Fluent Emoji 3D (licença MIT) — ver assets/pets/LICENSE-fluent-emoji.txt
export const SKINS = [
  { id: 'panda', name: 'Panda', level: 1, image: require('../../assets/pets/panda.png'), tint: '#ece8fb' },
  { id: 'hamster', name: 'Hamster', level: 1, image: require('../../assets/pets/hamster.png'), tint: '#fdeedd' },
  { id: 'coelho', name: 'Coelho', level: 2, image: require('../../assets/pets/rabbit_face.png'), tint: '#f2f0f5' },
  { id: 'raposa', name: 'Raposa', level: 3, image: require('../../assets/pets/fox.png'), tint: '#fde6d6' },
  { id: 'gato', name: 'Gato', level: 4, image: require('../../assets/pets/cat_face.png'), tint: '#fdf1d8' },
  { id: 'coala', name: 'Coala', level: 5, image: require('../../assets/pets/koala.png'), tint: '#e9eef2' },
  { id: 'sapo', name: 'Sapo', level: 6, image: require('../../assets/pets/frog.png'), tint: '#e3f3dc' },
];

export const DEFAULT_SKIN = SKINS[0];

export function findSkin(id) {
  return SKINS.find(skin => skin.id === id) || DEFAULT_SKIN;
}

export function isUnlocked(skin, level) {
  return (level || 1) >= skin.level;
}

const storageKey = userId => `@buddy_skin_${userId}`;

export async function loadSkin(userId, level) {
  const saved = findSkin(await AsyncStorage.getItem(storageKey(userId)));
  return isUnlocked(saved, level) ? saved : DEFAULT_SKIN;
}

export async function saveSkin(userId, skinId) {
  await AsyncStorage.setItem(storageKey(userId), skinId);
}
