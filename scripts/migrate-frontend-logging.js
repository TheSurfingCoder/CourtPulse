#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const filePath = '/Users/mbp/Codingprojects/Portfolio-Projects/CourtPulse/frontend/components/CourtsMap.tsx';

console.log('Migrating frontend logging...');

let content = fs.readFileSync(filePath, 'utf8');

// Pattern to match console.log(JSON.stringify({...}))
const pattern = /console\.log\(JSON\.stringify\(\s*\{([\s\S]*?)\}\s*\)\)/g;

let match;
let replacementCount = 0;

while ((match = pattern.exec(content)) !== null) {
  const jsonContent = match[1];
  
  // Extract event name from the JSON content
  const eventMatch = jsonContent.match(/event:\s*['"`]([^'"`]+)['"`]/);
  const eventName = eventMatch ? eventMatch[1] : 'unknown_event';
  
  // Remove timestamp and event fields from the JSON content
  const cleanedJson = jsonContent
    .replace(/event:\s*['"`][^'"`]+['"`],?\s*/g, '')
    .replace(/timestamp:\s*new Date\(\)\.toISOString\(\),?\s*/g, '')
    .replace(/,\s*$/, '') // Remove trailing comma
    .trim();
  
  // Create the replacement
  const replacement = `logEvent('${eventName}', ${cleanedJson ? `{${cleanedJson}}` : '{}'})`;
  
  // Replace in content
  content = content.replace(match[0], replacement);
  replacementCount++;
  
  console.log(`✅ Migrated: ${eventName}`);
}

// Write the updated content back
fs.writeFileSync(filePath, content);

console.log(`\n🎉 Migration complete! Replaced ${replacementCount} logging statements.`);
