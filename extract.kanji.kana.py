#!/bin/python

import re
import sys

def separation_kanji_kana(texte):
    # Utilisation d'expressions régulières pour identifier les kanjis et les kana
    kanji = re.findall(r'[\u4e00-\u9faf]', texte)  # plage Unicode des kanjis
    kana = re.findall(r'[\u3040-\u30ffー]+', texte)  # plage Unicode des kana

    return kanji, kana

def sort_output_uniq(list):
    count=0
    out=[]
    for e in list:
      if len(e) != 1:
        sort_output_uniq(e)
      else:
        if e not in out:
          out.append(e) 
          count+=1
    return out,count

def main():
    print(sys.argv)
    #['example.py', 'one', 'two', 'three']
    if len(sys.argv) < 2:
      print('need filename')
      exit(1)
    print("Using file {}".format(sys.argv[1]))
    nom_fichier=(sys.argv[1])
    with open(nom_fichier, 'r', encoding='utf-16', errors='ignore') as fichier:
        texte_japonais = fichier.read()

    kanji, kana = separation_kanji_kana(texte_japonais)
   
    kanji,c1=sort_output_uniq(kanji)
    kana,c2=sort_output_uniq(kana)
    print("{} Kanjis trouvés : {} ".format(c1," ".join(kanji)))
    print("{} Kana trouvés : {} ".format(c2," ".join(kana)))

if __name__ == "__main__":
    main()

