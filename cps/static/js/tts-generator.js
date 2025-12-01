#!/usr/bin/env node

/**
 * Text-to-Speech Generator with cross-platform support
 * This script is called by Python to generate audio files
 * Supports: macOS (say), Windows (say), Linux (espeak/festival)
 */

const fs = require('fs');
const path = require('path');
const { execSync, exec } = require('child_process');
const os = require('os');

// Parse command line arguments
const args = process.argv.slice(2);

if (args.length < 3) {
  console.error('Usage: node tts-generator.js <text> <output_file> <voice> [speed]');
  console.error('Example: node tts-generator.js "Hello world" output.mp3 "default" 1.0');
  process.exit(1);
}

let text = args[0];
const outputFile = args[1];
const voice = args[2] || 'default';
const speed = parseFloat(args[3]) || 1.0;

// Determine output format from file extension
const outputFormat = path.extname(outputFile).toLowerCase();

// Check if text starts with @ (file reference)
if (text.startsWith('@')) {
  const textFile = text.substring(1);
  try {
    text = fs.readFileSync(textFile, 'utf-8');
    console.log(`Read text from file: ${textFile}`);
  } catch (err) {
    console.error(`Error reading text file: ${err.message}`);
    process.exit(1);
  }
}

// Ensure output directory exists
const outputDir = path.dirname(outputFile);
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

// Detect platform
const platform = os.platform();
console.log(`Platform detected: ${platform}`);

// Generate audio
console.log(`Generating audio...`);
console.log(`- Platform: ${platform}`);
console.log(`- Text length: ${text.length} characters`);
console.log(`- Output: ${outputFile}`);
console.log(`- Voice (original): ${voice}`);
console.log(`- Speed: ${speed}`);

/**
 * Generate audio using platform-specific TTS
 */
function generateAudio() {
  try {
    if (platform === 'darwin') {
      // macOS - use native 'say' command
      generateAudioMacOS();
    } else if (platform === 'win32') {
      // Windows - use 'say' library
      generateAudioWindows();
    } else {
      // Linux - use espeak or festival
      generateAudioLinux();
    }
  } catch (err) {
    console.error('Error generating audio:', err.message);
    process.exit(1);
  }
}

/**
 * macOS TTS using native 'say' command
 */
function generateAudioMacOS() {
  const tempAiff = path.join(os.tmpdir(), `tts_${Date.now()}.aiff`);

  // Write text to temp file to avoid command line length limits
  const tempTextFile = path.join(os.tmpdir(), `tts_${Date.now()}.txt`);
  fs.writeFileSync(tempTextFile, text);

  try {
    // Generate AIFF file
    const sayCmd = `say -f "${tempTextFile}" -v "${voice}" -r ${Math.round(speed * 175)} -o "${tempAiff}"`;
    console.log(`Executing command: ${sayCmd}`);
    execSync(sayCmd);

    // Convert AIFF to desired format using ffmpeg
    if (commandExists('ffmpeg')) {
      if (outputFormat === '.mp3') {
        // Convert to MP3 with good quality and compression
        execSync(`ffmpeg -i "${tempAiff}" -codec:a libmp3lame -qscale:a 2 -y "${outputFile}"`);
      } else {
        // Convert to WAV or other format
        execSync(`ffmpeg -i "${tempAiff}" -y "${outputFile}"`);
      }
    } else if (commandExists('afconvert')) {
      if (outputFormat === '.mp3') {
        console.error('Warning: afconvert cannot create MP3. Install ffmpeg for MP3 support.');
        // Fallback to WAV
        const wavFile = outputFile.replace('.mp3', '.wav');
        execSync(`afconvert -f WAVE -d LEI16 "${tempAiff}" "${wavFile}"`);
        fs.renameSync(wavFile, outputFile);
      } else {
        execSync(`afconvert -f WAVE -d LEI16 "${tempAiff}" "${outputFile}"`);
      }
    } else {
      // Just rename if no converter available
      console.error('Warning: No audio converter found. Output may not be in desired format.');
      fs.renameSync(tempAiff, outputFile);
    }

    // Cleanup
    if (fs.existsSync(tempAiff)) {
      fs.unlinkSync(tempAiff);
    }
    fs.unlinkSync(tempTextFile);

    verifyOutput();
  } catch (err) {
    // Cleanup on error
    if (fs.existsSync(tempTextFile)) fs.unlinkSync(tempTextFile);
    if (fs.existsSync(tempAiff)) fs.unlinkSync(tempAiff);
    throw err;
  }
}

/**
 * Windows TTS using 'say' library
 */
function generateAudioWindows() {
  const say = require('say');

  say.export(text, voice, speed, outputFile, (err) => {
    if (err) {
      console.error('Error generating audio:', err);
      process.exit(1);
    }
    verifyOutput();
  });
}

/**
 * Linux TTS using espeak-ng or festival
 */
function generateAudioLinux() {
  // Try espeak-ng first (better quality), then espeak, then festival
  if (commandExists('espeak-ng')) {
    generateWithEspeak('espeak-ng');
  } else if (commandExists('espeak')) {
    generateWithEspeak('espeak');
  } else if (commandExists('festival')) {
    generateWithFestival();
  } else {
    throw new Error('No TTS engine found. Please install espeak-ng, espeak, or festival');
  }
}

/**
 * Generate audio using espeak/espeak-ng
 */
function generateWithEspeak(command) {
  console.log(`Using ${command} for TTS`);

  // Write text to temp file
  const tempTextFile = path.join(os.tmpdir(), `tts_${Date.now()}.txt`);
  fs.writeFileSync(tempTextFile, text);

  try {
    const speedWpm = Math.round(speed * 175);
    const espeakVoice = mapVoiceToEspeak(voice);
    console.log(`Voice mapping: ${voice} -> ${espeakVoice}`);

    if (outputFormat === '.mp3' && commandExists('ffmpeg')) {
      // Generate WAV first, then convert to MP3
      const tempWav = path.join(os.tmpdir(), `tts_${Date.now()}.wav`);
      const cmd = `${command} -f "${tempTextFile}" -w "${tempWav}" -s ${speedWpm} -v ${espeakVoice}`;
      console.log(`Executing: ${cmd}`);
      execSync(cmd);

      // Convert to MP3
      const ffmpegCmd = `ffmpeg -i "${tempWav}" -codec:a libmp3lame -qscale:a 2 -y "${outputFile}"`;
      console.log(`Converting to MP3: ${ffmpegCmd}`);
      execSync(ffmpegCmd);

      // Cleanup temp WAV
      if (fs.existsSync(tempWav)) fs.unlinkSync(tempWav);
    } else {
      // Generate WAV directly
      const cmd = `${command} -f "${tempTextFile}" -w "${outputFile}" -s ${speedWpm} -v ${espeakVoice}`;
      console.log(`Executing: ${cmd}`);
      execSync(cmd);
    }

    // Cleanup
    fs.unlinkSync(tempTextFile);

    verifyOutput();
  } catch (err) {
    if (fs.existsSync(tempTextFile)) fs.unlinkSync(tempTextFile);
    throw err;
  }
}

/**
 * Generate audio using festival
 */
function generateWithFestival() {
  console.log('Using festival for TTS');

  // Write text to temp file
  const tempTextFile = path.join(os.tmpdir(), `tts_${Date.now()}.txt`);
  fs.writeFileSync(tempTextFile, text);

  try {
    // Festival script
    const festivalScript = `(begin
  (set! utt1 (Utterance Text "${text.replace(/"/g, '\\"')}"))
  (utt.synth utt1)
  (utt.save.wave utt1 "${outputFile}")
)`;

    const tempScriptFile = path.join(os.tmpdir(), `tts_script_${Date.now()}.scm`);
    fs.writeFileSync(tempScriptFile, festivalScript);

    execSync(`festival -b "${tempScriptFile}"`);

    // Cleanup
    fs.unlinkSync(tempTextFile);
    fs.unlinkSync(tempScriptFile);

    verifyOutput();
  } catch (err) {
    if (fs.existsSync(tempTextFile)) fs.unlinkSync(tempTextFile);
    throw err;
  }
}

/**
 * Map voice names to espeak voices
 */
function mapVoiceToEspeak(voiceName) {
  const voiceMap = {
    // macOS English voices -> espeak English
    'Alex': 'en-us',
    'Samantha': 'en-us',
    'Victoria': 'en-us',
    'Daniel': 'en-gb',
    'Karen': 'en-au',

    // macOS Spanish voices -> espeak Spanish
    'Monica': 'es',
    'Jorge': 'es',
    'Paulina': 'es-la',

    // Generic language codes
    'default': 'en',
    'en': 'en',
    'en-us': 'en-us',
    'en-gb': 'en-gb',
    'es': 'es',
    'es-la': 'es-la',
    'fr': 'fr',
    'de': 'de',
    'it': 'it',
    'pt': 'pt',
    'ru': 'ru',
    'zh': 'zh',
    'ja': 'ja'
  };

  return voiceMap[voiceName] || voiceMap[voiceName.toLowerCase()] || 'en';
}

/**
 * Check if a command exists
 */
function commandExists(command) {
  try {
    const checkCmd = platform === 'win32' ? 'where' : 'which';
    execSync(`${checkCmd} ${command}`, { stdio: 'ignore' });
    return true;
  } catch (err) {
    return false;
  }
}

/**
 * Verify output file was created successfully
 */
function verifyOutput() {
  if (fs.existsSync(outputFile)) {
    const stats = fs.statSync(outputFile);
    console.log(`Audio generated successfully!`);
    console.log(`File size: ${stats.size} bytes`);
    process.exit(0);
  } else {
    console.error('Error: Output file was not created');
    process.exit(1);
  }
}

// Start generation
generateAudio();
