export function audioCodecLabel(codec: API.AudioCodecFamily): string {
  return codec === 'none' ? '无音轨' : codec.toUpperCase();
}
