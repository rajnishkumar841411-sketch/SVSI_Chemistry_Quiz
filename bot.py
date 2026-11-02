import os
import json
import time
import sqlite3
import logging
import threading
from flask import Flask, request, jsonify
import requests
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('svsi-quiz')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '').strip()
CHANNEL_ID = os.environ.get('CHANNEL_ID', '@Svsi70').strip()
BOT_USERNAME = os.environ.get('BOT_USERNAME', '').strip().lstrip('@')
ADMIN_IDS = {x.strip() for x in os.environ.get('ADMIN_IDS', '').split(',') if x.strip()}
PUBLIC_URL = os.environ.get('RENDER_EXTERNAL_URL', '').strip().rstrip('/')
DB_PATH = os.environ.get('DB_PATH', '/tmp/svsi_quiz.sqlite3')
app = Flask(__name__)
API = f'https://api.telegram.org/bot{BOT_TOKEN}' if BOT_TOKEN else ''
db_lock = threading.Lock()
QUESTIONS = [('किस सांद्रता पद का मान तापमान पर निर्भर नहीं करता?', ['मोलरता', 'मोललता', 'नॉर्मलता', 'फॉर्मलता'], 1, 'मोललता विलायक के द्रव्यमान पर आधारित होती है, आयतन पर नहीं।'), ('आदर्श विलयन Raoult के नियम का पालन करता है:', ['केवल कम सांद्रता पर', 'केवल उच्च ताप पर', 'सभी संघटनों पर', 'किसी भी दशा में नहीं'], 2, 'आदर्श विलयन सभी संघटनों पर Raoult के नियम का पालन करता है।'), ('परासरण दाब का सूत्र कौन-सा है?', ['π = CRT', 'π = C/R', 'π = RT/C', 'π = C + RT'], 0, 'पतले विलयन के लिए π = CRT।'), ('वान्ट हॉफ गुणांक i का मान संघटन के किस प्रभाव को दर्शाता है?', ['रंग', 'विलेय कणों की संख्या में परिवर्तन', 'घनत्व', 'श्यानता'], 1, 'वियोजन या संगुणन से कणों की संख्या बदलती है।'), ('किस गुणधर्म से अणुभार ज्ञात किया जा सकता है?', ['रंग', 'कोलिगेटिव गुण', 'अपवर्तनांक मात्र', 'चुंबकीय आघूर्ण'], 1, 'कोलिगेटिव गुण विलेय कणों की संख्या पर निर्भर करते हैं।'), ('हेनरी का नियम किससे संबंधित है?', ['गैस की द्रव में विलेयता', 'ठोस का गलनांक', 'अम्ल की शक्ति', 'विद्युत चालकता'], 0, 'निश्चित ताप पर गैस की विलेयता उसके आंशिक दाब के समानुपाती होती है।'), ('मोलर चालकता की SI इकाई है:', ['S m² mol⁻¹', 'S m⁻¹', 'ohm m', 'mol L⁻¹'], 0, 'मोलर चालकता की इकाई सीमेंस मीटर² प्रति मोल है।'), ('डेनियल सेल में एनोड कौन-सा है?', ['Cu', 'Zn', 'Ag', 'Pt'], 1, 'जिंक का ऑक्सीकरण होता है, इसलिए Zn एनोड है।'), ('गैल्वेनी सेल में ऑक्सीकरण कहाँ होता है?', ['कैथोड', 'एनोड', 'लवण सेतु', 'दोनों इलेक्ट्रोड पर'], 1, 'ऑक्सीकरण हमेशा एनोड पर होता है।'), ('मानक हाइड्रोजन इलेक्ट्रोड का मानक विभव कितना माना जाता है?', ['1.00 V', '0.00 V', '−1.00 V', '0.76 V'], 1, 'SHE का मानक इलेक्ट्रोड विभव शून्य निर्धारित किया गया है।'), ('फैराडे स्थिरांक का लगभग मान है:', ['96500 C mol⁻¹', '8.314 J mol⁻¹ K⁻¹', '6.022×10²³', '1.6×10⁻¹⁹ C'], 0, 'एक मोल इलेक्ट्रॉनों का आवेश लगभग 96500 कूलॉम है।'), ('विद्युत अपघटन में कैथोड पर कौन-सी प्रक्रिया होती है?', ['ऑक्सीकरण', 'अपचयन', 'उदासीनीकरण', 'जलयोजन'], 1, 'कैथोड पर इलेक्ट्रॉन ग्रहण अर्थात अपचयन होता है।'), ('सेल का EMF अधिकतम कब होता है?', ['जब सेल में धारा न बह रही हो', 'जब बहुत अधिक धारा बहे', 'जब सेल गर्म हो', 'जब इलेक्ट्रोड हटे हों'], 0, 'EMF खुले परिपथ में मापा जाता है, जब धारा शून्य होती है।'), ('प्रथम कोटि अभिक्रिया के वेग स्थिरांक की इकाई है:', ['mol L⁻¹ s⁻¹', 's⁻¹', 'L mol⁻¹ s⁻¹', 'mol² L⁻² s⁻¹'], 1, 'प्रथम कोटि के लिए k की इकाई समय⁻¹ होती है।'), ('प्रथम कोटि अभिक्रिया की अर्ध-आयु निर्भर करती है:', ['प्रारंभिक सांद्रता पर', 'केवल k पर', 'दाब पर ही', 'उत्प्रेरक के रंग पर'], 1, 't½ = 0.693/k, अतः प्रारंभिक सांद्रता से स्वतंत्र है।'), ('अभिक्रिया की आणविकता हमेशा होती है:', ['शून्य या ऋणात्मक', 'पूर्णांक', 'भिन्नात्मक', 'ऋणात्मक'], 1, 'एक प्राथमिक चरण में टकराने वाले कणों की संख्या पूर्णांक होती है।'), ('ताप बढ़ाने पर सामान्यतः अभिक्रिया का वेग:', ['घटता है', 'बढ़ता है', 'शून्य हो जाता है', 'अपरिवर्तित रहता है'], 1, 'ताप बढ़ने से अधिक अणुओं के पास सक्रियण ऊर्जा होती है।'), ('Arrhenius समीकरण में सक्रियण ऊर्जा का प्रतीक है:', ['Ea', 'ΔH', 'ΔS', 'π'], 0, 'Arrhenius समीकरण में Ea सक्रियण ऊर्जा है।'), ('d-ब्लॉक तत्वों में परिवर्तनशील ऑक्सीकरण अवस्था का कारण है:', ['ns और (n−1)d कक्षकों की ऊर्जा में निकटता', 'केवल बड़ा आकार', 'पूर्ण p-कक्षक', 'कम घनत्व'], 0, 'ns तथा (n−1)d इलेक्ट्रॉनों की ऊर्जा में अंतर कम होता है।'), ('KMnO₄ में Mn की ऑक्सीकरण अवस्था है:', ['+2', '+4', '+6', '+7'], 3, 'K(+1) और O(−2) से Mn की अवस्था +7 आती है।'), ('लैंथेनाइड संकुचन का मुख्य कारण है:', ['4f इलेक्ट्रॉनों का कमजोर परिरक्षण', '5d का पूर्ण भरना', 'परमाणु द्रव्यमान घटना', 'नाभिकीय आवेश घटना'], 0, '4f इलेक्ट्रॉन प्रभावी परिरक्षण कम करते हैं।'), ('Zn को संक्रमण तत्व नहीं माना जाता क्योंकि:', ['इसका परमाणु छोटा है', 'Zn और Zn²⁺ में d-कक्षक पूर्ण भरे हैं', 'यह रंगहीन है', 'यह गैस है'], 1, 'Zn तथा Zn²⁺ दोनों में d¹⁰ विन्यास होता है।'), ('KMnO₄ का रंग है:', ['हरा', 'बैंगनी', 'पीला', 'नीला'], 1, 'परमैंगनेट आयन बैंगनी रंग का होता है।'), ('[Co(NH₃)₆]Cl₃ में Co की ऑक्सीकरण अवस्था है:', ['+1', '+2', '+3', '+6'], 2, 'NH₃ उदासीन है और तीन Cl⁻ बाहरी आयन हैं, इसलिए Co +3 है।'), ('समन्वय संख्या किसे कहते हैं?', ['केंद्रीय धातु से जुड़े दाता परमाणुओं की संख्या', 'लिगैंड का द्रव्यमान', 'धातु का परमाणु क्रमांक', 'आयन का आवेश'], 0, 'केंद्रीय धातु से सीधे जुड़े दाता परमाणुओं की संख्या समन्वय संख्या है।'), ('EDTA किस प्रकार का लिगैंड है?', ['एकदंती', 'द्विदंती', 'षट्दंती', 'उदासीन'], 2, 'EDTA छह दाता स्थलों से जुड़ सकता है।'), ('[Ni(CO)₄] की ज्यामिति है:', ['वर्ग समतलीय', 'चतुष्फलकीय', 'अष्टफलकीय', 'रैखिक'], 1, 'Ni(CO)₄ चतुष्फलकीय और प्रतिचुंबकीय है।'), ('लिगैंड NH₃ का नाम है:', ['अम्मीन', 'एक्वा', 'कार्बोनिल', 'नाइट्रो'], 0, 'समन्वय यौगिकों में NH₃ को ammine कहते हैं।'), ('CH₃Cl का IUPAC नाम है:', ['क्लोरोमीथेन', 'मेथिलीन क्लोराइड', 'क्लोरोएथेन', 'क्लोरोफॉर्म'], 0, 'एक कार्बन वाले ऐल्केन का नाम मीथेन है।'), ('SN1 अभिक्रिया में मध्यवर्ती बनता है:', ['कार्बोकैटायन', 'कार्बऐनायन', 'मुक्त मूलक', 'कार्बीन'], 0, 'SN1 दो चरणों में होती है और कार्बोकैटायन बनता है।'), ('क्लोरोबेंजीन में C–Cl बंध कम क्रियाशील होता है क्योंकि:', ['अनुनाद से आंशिक द्विबंध गुण', 'बंध आयनिक है', 'कार्बन sp³ है', 'क्लोरीन छोटा है'], 0, 'अनुनाद के कारण C–Cl बंध में आंशिक द्विबंध गुण आता है।'), ('वुर्ट्ज अभिक्रिया में प्रयुक्त धातु है:', ['Na', 'Fe', 'Cu', 'Ag'], 0, 'ऐल्किल हैलाइड सोडियम के साथ शुष्क ईथर में युग्मित होते हैं।'), ('ऐल्कोहॉल में –OH समूह जुड़ा होता है:', ['संतृप्त C से', 'केवल बेंजीन वलय से', 'धातु से', 'कार्बोनिल O से'], 0, 'ऐल्कोहॉल में हाइड्रॉक्सिल समूह संतृप्त कार्बन से जुड़ा रहता है।'), ('फीनॉल, ऐल्कोहॉल से अधिक अम्लीय है क्योंकि:', ['फीनॉक्साइड आयन अनुनाद से स्थिर होता है', 'इसका द्रव्यमान अधिक है', 'यह गैस है', 'इसमें H नहीं है'], 0, 'फीनॉक्साइड आयन अनुनाद द्वारा स्थायित्व प्राप्त करता है।'), ('प्राथमिक ऐल्कोहॉल के नियंत्रित ऑक्सीकरण से बनता है:', ['ऐल्डिहाइड', 'कीटोन', 'ईथर', 'ऐल्कीन'], 0, 'प्राथमिक ऐल्कोहॉल का नियंत्रित ऑक्सीकरण ऐल्डिहाइड देता है।'), ('ईथर का सामान्य क्रियात्मक समूह है:', ['R–O–R′', 'R–CHO', 'R–COOH', 'R–NH₂'], 0, 'ईथर में ऑक्सीजन दो कार्बनिक समूहों के बीच होती है।'), ('विलियमसन संश्लेषण से बनते हैं:', ['ईथर', 'ऐमीन', 'ऐल्डिहाइड', 'कार्बोक्सिलिक अम्ल'], 0, 'ऐल्कॉक्साइड और प्राथमिक ऐल्किल हैलाइड से ईथर बनता है।'), ('ऐल्डिहाइड का क्रियात्मक समूह है:', ['–CHO', '–CO–', '–COOH', '–OH'], 0, 'ऐल्डिहाइड में टर्मिनल –CHO समूह होता है।'), ('टॉलेंस अभिकर्मक किसकी पहचान में उपयोगी है?', ['ऐल्डिहाइड', 'ऐल्केन', 'ईथर', 'ऐल्कोहॉल'], 0, 'ऐल्डिहाइड टॉलेंस अभिकर्मक को अपचयित कर रजत दर्पण देता है।'), ('कीटोन का क्रियात्मक समूह है:', ['>C=O', '–CHO', '–COOH', '–NH₂'], 0, 'कीटोन में कार्बोनिल समूह दो कार्बन समूहों के बीच होता है।'), ('कार्बोक्सिलिक अम्ल का क्रियात्मक समूह है:', ['–COOH', '–CHO', '–OH', '–X'], 0, 'कार्बोक्सिल समूह –COOH होता है।'), ('कार्बोक्सिलिक अम्ल, फीनॉल से सामान्यतः:', ['अधिक अम्लीय हैं', 'कम अम्लीय हैं', 'समान अम्लीय हैं', 'क्षारीय हैं'], 0, 'कार्बोक्सिलेट आयन अनुनाद से अधिक स्थिर होता है।'), ('ऐनिलीन का सूत्र है:', ['C₆H₅NH₂', 'C₆H₆', 'C₆H₅OH', 'C₆H₅CH₃'], 0, 'ऐनिलीन बेंजीन पर जुड़ा –NH₂ समूह है।'), ('ऐमीनों में क्षारीयता का कारण है:', ['N पर एकाकी इलेक्ट्रॉन युग्म', 'केवल N–H बंध', 'ऑक्सीजन', 'कार्बोनिल समूह'], 0, 'नाइट्रोजन का lone pair प्रोटॉन ग्रहण कर सकता है।'), ('कार्बाइलऐमीन परीक्षण किसके लिए दिया जाता है?', ['प्राथमिक ऐमीन', 'द्वितीयक ऐमीन', 'तृतीयक ऐमीन', 'सभी ऐमीन'], 0, 'प्राथमिक ऐमीन क्लोरोफॉर्म और क्षार के साथ दुर्गंधयुक्त आइसोसायनाइड देते हैं।'), ('डायजोनीकरण अभिक्रिया सामान्यतः किस ताप पर की जाती है?', ['0–5°C', '25–30°C', '50–60°C', '100°C'], 0, 'बेंजीन डायजोनीयम लवण कम ताप पर स्थिर रहते हैं।'), ('ग्लूकोज किस प्रकार का कार्बोहाइड्रेट है?', ['मोनोसैकराइड', 'डाइसैकराइड', 'पॉलीसैकराइड', 'प्रोटीन'], 0, 'ग्लूकोज एकल शर्करा अर्थात मोनोसैकराइड है।'), ('सुक्रोज के जल-अपघटन से प्राप्त होते हैं:', ['ग्लूकोज और फ्रक्टोज', 'दो ग्लूकोज', 'ग्लूकोज और गैलेक्टोज', 'दो फ्रक्टोज'], 0, 'सुक्रोज से ग्लूकोज और फ्रक्टोज बनते हैं।'), ('स्टार्च किसका बहुलक है?', ['α-D-ग्लूकोज', 'β-D-ग्लूकोज', 'फ्रक्टोज', 'अमीनो अम्ल'], 0, 'स्टार्च α-D-ग्लूकोज इकाइयों से बना है।'), ('प्रोटीन की मूल इकाइयाँ हैं:', ['अमीनो अम्ल', 'न्यूक्लियोटाइड', 'फैटी अम्ल', 'ग्लूकोज'], 0, 'प्रोटीन अमीनो अम्लों के बहुलक हैं।'), ('पेप्टाइड बंध किसके बीच बनता है?', ['दो अमीनो अम्लों के बीच', 'दो ग्लूकोज के बीच', 'दो न्यूक्लियोटाइड के बीच', 'दो वसीय अम्लों के बीच'], 0, 'एक अमीनो अम्ल का –COOH और दूसरे का –NH₂ समूह जुड़ते हैं।'), ('DNA में कौन-सी शर्करा होती है?', ['2-डिऑक्सीराइबोज', 'राइबोज', 'ग्लूकोज', 'फ्रक्टोज'], 0, 'DNA में 2-deoxyribose शर्करा होती है।'), ('RNA में थायमिन के स्थान पर कौन-सा क्षारक होता है?', ['यूरैसिल', 'एडेनिन', 'ग्वानिन', 'साइटोसिन'], 0, 'RNA में थायमिन के स्थान पर यूरैसिल होता है।'), ('विटामिन C का रासायनिक नाम है:', ['एस्कॉर्बिक अम्ल', 'रेटिनॉल', 'कैल्सीफेरॉल', 'टोकोफेरॉल'], 0, 'विटामिन C एस्कॉर्बिक अम्ल है।'), ('विटामिन D की कमी से बच्चों में होता है:', ['रिकेट्स', 'स्कर्वी', 'बेरी-बेरी', 'रतौंधी'], 0, 'विटामिन D की कमी से हड्डियों का खनिजीकरण प्रभावित होता है।'), ('एंजाइम मुख्यतः किस प्रकृति के होते हैं?', ['प्रोटीन', 'कार्बोहाइड्रेट', 'वसा', 'अकार्बनिक लवण'], 0, 'अधिकांश एंजाइम प्रोटीन होते हैं।'), ('साबुन किसके सोडियम या पोटैशियम लवण होते हैं?', ['उच्च वसीय अम्ल', 'खनिज अम्ल', 'अमीनो अम्ल', 'कार्बोनिक अम्ल'], 0, 'साबुन उच्च वसीय अम्लों के Na⁺/K⁺ लवण हैं।'), ('डिटर्जेंट कठोर जल में भी प्रभावी रहते हैं क्योंकि:', ['वे Ca²⁺/Mg²⁺ के अघुलनशील लवण कम बनाते हैं', 'वे जल को उबालते हैं', 'वे अम्ल हैं', 'वे गैस बनाते हैं'], 0, 'सिंथेटिक डिटर्जेंट कठोर जल में भी झाग और सफाई देते हैं।'), ('अभिक्रिया की दर की सामान्य इकाई हो सकती है:', ['mol L⁻¹ s⁻¹', 's⁻¹ केवल', 'mol²', 'L mol⁻¹'], 0, 'दर सांद्रता में परिवर्तन प्रति समय है।'), ('शून्य कोटि अभिक्रिया में दर:', ['सांद्रता से स्वतंत्र', 'सांद्रता के समानुपाती', 'सांद्रता के वर्ग के समानुपाती', 'हमेशा शून्य'], 0, 'शून्य कोटि में दर = k होती है।'), ('लवण सेतु का मुख्य कार्य है:', ['विद्युत उदासीनता बनाए रखना', 'इलेक्ट्रॉन देना', 'ताप बढ़ाना', 'इलेक्ट्रोड घोलना'], 0, 'लवण सेतु आयनों के प्रवाह से दोनों अर्ध-सेलों में आवेश संतुलित रखता है।'), ('विशिष्ट चालकता का SI मात्रक है:', ['S m⁻¹', 'S m² mol⁻¹', 'ohm', 'mol m⁻³'], 0, 'विशिष्ट चालकता की SI इकाई सीमेंस प्रति मीटर है।'), ('कोलिगेटिव गुणों की संख्या में कौन शामिल नहीं है?', ['श्यानता', 'वाष्प दाब का आपेक्षिक अवनमन', 'क्वथनांक उन्नयन', 'हिमांक अवनमन'], 0, 'श्यानता कोलिगेटिव गुण नहीं है।'), ('अष्टफलकीय संकुल में समन्वय संख्या होती है:', ['2', '4', '6', '8'], 2, 'अष्टफलकीय संकुल में केंद्रीय धातु से छह दाता परमाणु जुड़े होते हैं।'), ('[Ag(NH₃)₂]⁺ में Ag की ऑक्सीकरण अवस्था है:', ['0', '+1', '+2', '+3'], 1, 'NH₃ उदासीन है और संकुल का कुल आवेश +1 है।'), ('फीनॉल, ब्रोमीन जल के साथ देता है:', ['2,4,6-ट्राइब्रोमोफीनॉल का सफेद अवक्षेप', 'नीला विलयन', 'रजत दर्पण', 'कोई अभिक्रिया नहीं'], 0, 'फीनॉल सक्रिय वलय के कारण ब्रोमीन जल से सफेद अवक्षेप देता है।'), ('फॉर्मेल्डिहाइड का IUPAC नाम है:', ['मेथेनल', 'एथेनल', 'प्रोपेनोन', 'मेथेनोइक अम्ल'], 0, 'एक कार्बन वाला ऐल्डिहाइड मेथेनल कहलाता है।'), ('एसीटोन का IUPAC नाम है:', ['प्रोपेनोन', 'प्रोपेनल', 'एथेनोन', 'ब्यूटेनोन'], 0, 'एसीटोन तीन कार्बन वाला कीटोन है: propanone।'), ('मिथाइल ऐमीन का सूत्र है:', ['CH₃NH₂', 'CH₃NO₂', 'CH₃OH', 'CH₃CN'], 0, 'मिथाइल ऐमीन में CH₃ समूह –NH₂ से जुड़ा है।'), ('न्यूक्लियोसाइड में होते हैं:', ['शर्करा और नाइट्रोजनी क्षारक', 'शर्करा और फॉस्फेट', 'क्षारक और फॉस्फेट', 'तीनों'], 0, 'न्यूक्लियोसाइड = शर्करा + नाइट्रोजनी क्षारक।')]
QUESTIONS = QUESTIONS[:70]

def init_db():
    with db_lock:
        con = sqlite3.connect(DB_PATH)
        con.execute('CREATE TABLE IF NOT EXISTS players(\n user_id TEXT PRIMARY KEY, name TEXT, q_index INTEGER DEFAULT 0,\n score INTEGER DEFAULT 0, active INTEGER DEFAULT 0, updated REAL\n )')
        con.commit()
        con.close()

def tg(method, payload=None):
    if not API:
        raise RuntimeError('BOT_TOKEN is missing')
    r = requests.post(f'{API}/{method}', json=payload or {}, timeout=25)
    data = r.json()
    if not data.get('ok'):
        raise RuntimeError(str(data))
    return data.get('result')

def send(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text}
    if reply_markup:
        data['reply_markup'] = reply_markup
    return tg('sendMessage', data)

def user_name(user):
    name = ' '.join((x for x in [user.get('first_name', ''), user.get('last_name', '')] if x)).strip()
    return name or user.get('username') or 'विद्यार्थी'

def is_admin(user_id):
    return str(user_id) in ADMIN_IDS

def keyboard_for(qnum):
    q = QUESTIONS[qnum]
    rows = []
    for i, option in enumerate(q[1]):
        rows.append([{'text': f"{'ABCD'[i]}. {option}", 'callback_data': f'ans:{qnum}:{i}'}])
    return {'inline_keyboard': rows}

def start_student(chat_id, user):
    uid = str(user['id'])
    name = user_name(user)
    with db_lock:
        con = sqlite3.connect(DB_PATH)
        con.execute('INSERT INTO players(user_id,name,q_index,score,active,updated)\n VALUES(?,?,0,0,1,?) ON CONFLICT(user_id) DO UPDATE SET\n name=excluded.name,q_index=0,score=0,active=1,updated=excluded.updated', (uid, name, time.time()))
        con.commit()
        con.close()
    send_question(chat_id, 0, first=True)

def send_question(chat_id, index, first=False):
    q = QUESTIONS[index]
    prefix = '🎓 SVSI Class 12 Chemistry Quiz\n\n' if first else ''
    msg = f'{prefix}प्रश्न {index + 1}/{len(QUESTIONS)}\n\n{q[0]}'
    send(chat_id, msg, keyboard_for(index))

def finish_quiz(chat_id, uid):
    with db_lock:
        con = sqlite3.connect(DB_PATH)
        row = con.execute('SELECT name,score FROM players WHERE user_id=?', (uid,)).fetchone()
        con.execute('UPDATE players SET active=0,updated=? WHERE user_id=?', (time.time(), uid))
        top = con.execute('SELECT name,score FROM players ORDER BY score DESC, updated ASC LIMIT 10').fetchall()
        con.commit()
        con.close()
    name, score = row if row else ('विद्यार्थी', 0)
    send(chat_id, f'🏁 क्विज़ पूरा हुआ!\n\n{name}\nआपका स्कोर: {score}/{len(QUESTIONS)}\n\nधन्यवाद! परिणाम लीडरबोर्ड में जोड़े गए हैं।')
    lines = ['🏆 SVSI Chemistry Quiz — Leaderboard']
    for i, (n, s) in enumerate(top, 1):
        lines.append(f'{i}. {n} — {s}/{len(QUESTIONS)}')
    try:
        send(CHANNEL_ID, '\n'.join(lines))
    except Exception:
        log.exception('Could not post leaderboard to channel')

def handle_message(msg):
    chat = msg.get('chat', {})
    user = msg.get('from', {})
    text = (msg.get('text') or '').strip()
    chat_id = chat.get('id')
    uid = str(user.get('id', ''))
    if not text or not user:
        return
    if text.startswith('/myid'):
        send(chat_id, f'आपकी Telegram ID: {uid}')
        return
    if text.startswith('/startquiz'):
        if not is_admin(uid):
            send(chat_id, 'यह कमांड केवल Admin चला सकता है।')
            return
        if chat.get('type') != 'private':
            send(chat_id, 'कृपया यह कमांड Bot की निजी चैट में भेजें।')
            return
        if not BOT_USERNAME:
            send(chat_id, 'सेटअप में BOT_USERNAME नहीं मिला है।')
            return
        link = f'https://t.me/{BOT_USERNAME}?start=quiz'
        try:
            send(CHANNEL_ID, '📢 SWAMI VIVEKANAND SCIENCE INSTITUTE\nClass 12 Chemistry — 70 MCQ Quiz\n\nक्विज़ में भाग लेने के लिए नीचे Start Quiz बटन दबाएँ।', {'inline_keyboard': [[{'text': '▶️ Start Quiz', 'url': link}]]})
            send(chat_id, '✅ Quiz announcement आपके चैनल पर भेज दिया गया है। विद्यार्थी चैनल के बटन से Bot में आकर Quiz शुरू कर सकते हैं।')
        except Exception as e:
            log.exception('Announcement failed')
            send(chat_id, f'चैनल पर संदेश नहीं भेज सका। Bot को चैनल में Admin और Post Messages अनुमति दें। विवरण: {e}')
        return
    if text.startswith('/leaderboard'):
        with db_lock:
            con = sqlite3.connect(DB_PATH)
            top = con.execute('SELECT name,score FROM players ORDER BY score DESC, updated ASC LIMIT 10').fetchall()
            con.close()
        lines = ['🏆 SVSI Chemistry Quiz — Leaderboard']
        lines += [f'{i}. {n} — {s}/{len(QUESTIONS)}' for i, (n, s) in enumerate(top, 1)]
        send(chat_id, '\n'.join(lines))
        return
    if text.startswith('/start'):
        if text.endswith('quiz') or 'quiz' in text:
            start_student(chat_id, user)
        else:
            send(chat_id, 'स्वागत है! 🎓\n\nक्विज़ में भाग लेने के लिए अपने संस्थान के Telegram चैनल में Start Quiz बटन दबाएँ।\n\nAdmin: क्विज़ की घोषणा के लिए /startquiz')
        return
    if text.startswith('/'):
        send(chat_id, 'क्विज़ शुरू करने के लिए /start दबाएँ।')
        return

def handle_callback(query):
    data = query.get('data', '')
    user = query.get('from', {})
    uid = str(user.get('id', ''))
    message = query.get('message', {})
    chat_id = message.get('chat', {}).get('id')
    message_id = message.get('message_id')
    if not data.startswith('ans:'):
        tg('answerCallbackQuery', {'callback_query_id': query['id']})
        return
    try:
        _, qstr, astr = data.split(':')
        q_index, answer = (int(qstr), int(astr))
    except Exception:
        tg('answerCallbackQuery', {'callback_query_id': query['id'], 'text': 'अमान्य विकल्प'})
        return
    with db_lock:
        con = sqlite3.connect(DB_PATH)
        row = con.execute('SELECT q_index,score,active FROM players WHERE user_id=?', (uid,)).fetchone()
        if not row or not row[2]:
            con.close()
            tg('answerCallbackQuery', {'callback_query_id': query['id'], 'text': 'पहले Quiz शुरू करें।'})
            return
        current, score, active = row
        if q_index != current:
            con.close()
            tg('answerCallbackQuery', {'callback_query_id': query['id'], 'text': 'यह प्रश्न पहले ही पूरा हो चुका है।'})
            return
        correct = QUESTIONS[q_index][2]
        is_right = answer == correct
        new_score = score + (1 if is_right else 0)
        next_index = current + 1
        con.execute('UPDATE players SET q_index=?,score=?,updated=? WHERE user_id=?', (next_index, new_score, time.time(), uid))
        con.commit()
        con.close()
    tg('answerCallbackQuery', {'callback_query_id': query['id'], 'text': 'सही उत्तर! +1' if is_right else 'गलत उत्तर। +0'})
    try:
        tg('editMessageReplyMarkup', {'chat_id': chat_id, 'message_id': message_id, 'reply_markup': {'inline_keyboard': []}})
    except Exception:
        pass
    explanation = QUESTIONS[q_index][3]
    send(chat_id, ('✅ सही उत्तर। +1 अंक\n' if is_right else f"❌ गलत उत्तर। सही उत्तर: {'ABCD'[correct]}. {QUESTIONS[q_index][1][correct]}\n") + explanation)
    if next_index >= len(QUESTIONS):
        finish_quiz(chat_id, uid)
    else:
        send_question(chat_id, next_index)

@app.route('/', methods=['GET'])
def home():
    return ('SVSI Chemistry Quiz Bot is running.', 200)

@app.route('/health', methods=['GET'])
def health():
    return (jsonify({'ok': True, 'questions': len(QUESTIONS)}), 200)

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    update = request.get_json(silent=True) or {}
    try:
        if 'message' in update:
            handle_message(update['message'])
        elif 'callback_query' in update:
            handle_callback(update['callback_query'])
    except Exception:
        log.exception('Update processing failed')
    return (jsonify({'ok': True}), 200)

def configure_webhook():
    if not BOT_TOKEN:
        log.error('BOT_TOKEN is missing; add it in Render Environment.')
        return
    if not PUBLIC_URL:
        log.error('RENDER_EXTERNAL_URL is missing; webhook cannot be configured.')
        return
    try:
        result = tg('setWebhook', {'url': PUBLIC_URL + '/telegram'})
        log.info('Webhook configured: %s', result)
    except Exception:
        log.exception('Webhook setup failed')
init_db()
configure_webhook()
