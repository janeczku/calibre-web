#!/usr/bin/env node

/**
 * Text-to-Speech Generator using 'say' library
 * This script is called by Python to generate audio files
 */

const say = require('say');
const fs = require('fs');
const path = require('path');

// Parse command line arguments
const args = process.argv.slice(2);

if (args.length < 3) {
  console.error('Usage: node tts-generator.js <text> <output_file> <voice> [speed]');
  console.error('Example: node tts-generator.js "Hello world" output.wav "Microsoft David Desktop" 1.0');
  process.exit(1);
}

let text = args[0];
const outputFile = args[1];
const voice = args[2] || null;
const speed = parseFloat(args[3]) || 1.0;

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

// Generate audio
console.log(`Generating audio...`);
console.log(`- Text length: ${text.length} characters`);
console.log(`- Output: ${outputFile}`);
console.log(`- Voice: ${voice || 'default'}`);
console.log(`- Speed: ${speed}`);

say.export(text, voice, speed, outputFile, (err) => {
  if (err) {
    console.error('Error generating audio:', err);
    process.exit(1);
  }

  console.log('Audio generated successfully!');

  // Verify file was created
  if (fs.existsSync(outputFile)) {
    const stats = fs.statSync(outputFile);
    console.log(`File size: ${stats.size} bytes`);
    process.exit(0);
  } else {
    console.error('Error: Output file was not created');
    process.exit(1);
  }
});
