import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const {PresentationFile,FileBlob}=await import(pathToFileURL(process.env.C360_ARTIFACT_MODULE).href);
const deck=await PresentationFile.importPptx(await FileBlob.load(path.resolve('output/presentation/customer360-technical.pptx')));
for(let i=0;i<deck.slides.items.length;i++){
 const blob=await deck.export({slide:deck.slides.items[i],format:'png',scale:1});
 await fs.writeFile(`tmp/deck/final-${i+1}.png`,new Uint8Array(await blob.arrayBuffer()));
}
console.log('Rendered '+deck.slides.items.length+' final slides');
