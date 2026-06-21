"use client";

import Image from 'next/image';
import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Languages,
  ArrowLeftRight,
  Copy,
  FileText,
  FileUp,
  Trash2,
  Download,
  TrendingUp,
  BookOpen,
  Users,
  Globe,
  Activity,
  CheckCircle2,
  Info,
  ChevronRight,
  Menu,
  X,
  Play,
  AlertCircle,
  Sun,
  Moon,
  MessageCircle,
  Maximize2,
  Minimize2,
  Send
} from 'lucide-react';

// --- TYPE DEFINITIONS & LOCAL DATA ---
type PageType = 'landing' | 'translator' | 'doc-translator' | 'detector' | 'insights' | 'about' | 'privacy' | 'terms';

interface TranslationResult {
  translatedText: string;
  politenessLevel: string;
  ngokoPercentage: number;
  kramaPercentage: number;
  context: string;
  alternativeText?: string;
  translationProvider?: string;
  apiConfidence?: number | null;
  usedFallback?: boolean;
}

interface DocumentTranslationResult {
  filename: string;
  downloadUrl: string;
  translatedText: string;
  previewTruncated: boolean;
  wordsTranslated: number;
  politenessSummary: string;
  sourceLang: string;
  targetLang: string;
}

interface InsightsResult {
  metrics: {
    total_vocabulary: number;
    total_vocab_usage?: number;
    active_contributors: number;
    vitality_status: string;
    preservation_accuracy: string;
    total_translations: number;
  };
  popular_words: {
    word: string;
    language: string;
    languageName?: string;
    count: number;
    meaning?: string;
    register?: string;
  }[];
}

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

const LOCAL_PHRASES: Record<string, Record<string, { high: string; low: string; context: string; altHigh?: string; altLow?: string }>> = {
  'id_jv': {
    'saya ingin makan nasi goreng': {
      high: 'Kula kersa dhahar sekul goreng.',
      low: 'Aku pengen mangan sego goreng.',
      context: 'Krama Alus (Sopan) digunakan untuk berbicara dengan orang tua/dihormati. Ngoko Lugu (Kasual) untuk teman sebaya.'
    },
    'kamu mau pergi ke mana': {
      high: 'Panjenengan badhe tindak dhateng pundi?',
      low: 'Kowe arep lungo nang endi?',
      context: 'Tingkat Krama menggunakan kata "Panjenengan" dan "Tindak" untuk menghormati lawan bicara.'
    },
    'terima kasih banyak atas bantuannya': {
      high: 'Matur nuwun sanget saking pitulunganipun.',
      low: 'Matur nuwun banget kanggo bantuane.',
      context: 'Kata "sanget" (sangat) dan "pitulunganipun" (bantuannya) mencerminkan kesopanan tingkat tinggi.'
    },
    'selamat pagi bagaimana kabar anda': {
      high: 'Sugeng enjang, kadospundi kabar panjenengan?',
      low: 'Sugeng enjing, piye kabarmu?',
      context: 'Sapaan formal menggunakan "Sugeng enjang" dan menanyakan kabar dengan "kadospundi".'
    },
    'nama saya ahmad saya tinggal di surabaya': {
      high: 'Nami kula Ahmad, kula dalem ing Surabaya.',
      low: 'Jenengku Ahmad, aku manggon ing Surabaya.',
      context: 'Menyebut diri sendiri di tingkat Krama menggunakan kata "Nami" (nama) dan "Dalem/Manggen" (tinggal).'
    },
    'aku sedang di jalan': {
      high: 'Kula wonten teng dalan',
      low: 'Aku neng dalan',
      context: 'Frasa "di jalan" dibaca sebagai keterangan tempat, bukan verba "berjalan".'
    },
    'saya sedang di jalan': {
      high: 'Kula wonten teng dalan',
      low: 'Aku neng dalan',
      context: 'Frasa "di jalan" dibaca sebagai keterangan tempat, bukan verba "berjalan".'
    },
    'aku di jalan': {
      high: 'Kula wonten teng dalan',
      low: 'Aku neng dalan',
      context: 'Frasa "di jalan" dibaca sebagai keterangan tempat, bukan verba "berjalan".'
    },
    'saya di jalan': {
      high: 'Kula wonten teng dalan',
      low: 'Aku neng dalan',
      context: 'Frasa "di jalan" dibaca sebagai keterangan tempat, bukan verba "berjalan".'
    }
  },
  'id_mad': {
    'saya ingin makan nasi goreng': {
      high: 'Bhiula terro neddha\'a nase\' goreng.',
      low: 'Sengko\' terro ngakana nase\' goreng.',
      context: 'Engghi-Bhanten menggunakan subjek "Bhiula" dan verba "neddha". Enja-Iya menggunakan "Sengko\'" dan "ngakan".'
    },
    'kamu mau pergi ke mana': {
      high: 'Panjhenengngan badhi alomampaha ka dhimma?',
      low: 'Ba\'na terro entarra ka dhimma?',
      context: 'Tingkat halus (Engghi-Bhanten) memakai kata "Panjhenengngan" dan verba halus "alomampah".'
    },
    'terima kasih banyak atas bantuannya': {
      high: 'Mator sakalangkong sanget saking bantoan panjhenengngan.',
      low: 'Sakalangkong raje saking bantoanna.',
      context: '"Sakalangkong" adalah frasa khas Madurese untuk berterima kasih. Penambahan "mator" menambah kesopanan.'
    },
    'selamat pagi bagaimana kabar anda': {
      high: 'Salamat pagi, kadospundi kabar panjhenengngan?',
      low: 'Salamat pagi, de\'remmah kabarra?',
      context: 'Menanyakan kabar secara kasual menggunakan kata "de\'remmah". Secara formal memakai "kadospundi".'
    },
    'nama saya ahmad saya tinggal di surabaya': {
      high: 'Nyama bhiula Ahmad, bhiula nengghu e Surabaya.',
      low: 'Nyama sengko\' Ahmad, sengko\' nyonggheng e Surabaya.',
      context: '"Nengghu" adalah bentuk halus Madura untuk tinggal/berkediaman, sedangkan "nyonggheng" bernada kasual.'
    }
  }
};

const ID_TO_JV_WORDS: Record<string, { high: string; low: string }> = {
  'saya': { high: 'kula', low: 'aku' },
  'kamu': { high: 'panjenengan', low: 'kowe' },
  'dia': { high: 'piyambakipun', low: 'dheweke' },
  'ingin': { high: 'badhe', low: 'pengen' },
  'makan': { high: 'dhahar', low: 'mangan' },
  'makanan': { high: 'dhaharan', low: 'panganan' },
  'nasi': { high: 'sekul', low: 'sego' },
  'minum': { high: 'ngunjuk', low: 'ngombe' },
  'tidur': { high: 'sare', low: 'turu' },
  'pergi': { high: 'tindak', low: 'lunga' },
  'ke': { high: 'dhateng', low: 'nang' },
  'mana': { high: 'pundi', low: 'endi' },
  'sini': { high: 'mriki', low: 'kene' },
  'sana': { high: 'mrika', low: 'kono' },
  'apa': { high: 'punapa', low: 'opo' },
  'siapa': { high: 'sinten', low: 'sopo' },
  'bagaimana': { high: 'kadospundi', low: 'piye' },
  'mengapa': { high: 'punapa amargi', low: 'kenopo' },
  'rumah': { high: 'griya', low: 'omah' },
  'air': { high: 'toya', low: 'banyu' },
  'jalan': { high: 'mlampah', low: 'mlaku' },
  'sekarang': { high: 'sakmenika', low: 'saiki' },
  'tidak': { high: 'mboten', low: 'ora' },
  'ya': { high: 'inggih', low: 'iyo' },
  'baik': { high: 'sae', low: 'apik' },
  'banyak': { high: 'kathah', low: 'akeh' },
  'sedikit': { high: 'sekedhik', low: 'sithik' },
  'besar': { high: 'ageng', low: 'gede' },
  'kecil': { high: 'alit', low: 'cilik' },
  'tua': { high: 'sepuh', low: 'tuwo' },
  'sangat': { high: 'sanget', low: 'banget' },
  'dari': { high: 'saking', low: 'soko' },
  'dan': { high: 'kaliyan', low: 'lan' },
  'dengan': { high: 'kaliyan', low: 'karo' },
  'bisa': { high: 'saged', low: 'iso' },
  'cara': { high: 'cara', low: 'cara' },
  'laku': { high: 'tindak', low: 'laku' },
  'menjalankan': { high: 'nindakaken', low: 'nglakoni' },
  'memperlakukan': { high: 'nindakaken', low: 'nglakoni' },
  'perlakukan': { high: 'nindakaken', low: 'nglakoni' }
};

const ID_TO_MAD_WORDS: Record<string, { high: string; low: string }> = {
  'saya': { high: 'bhiula', low: 'sengko\'' },
  'kamu': { high: 'panjhenengngan', low: 'ba\'na' },
  'dia': { high: 'dhibi\'na', low: 'dhibi\'na' },
  'ingin': { high: 'terro', low: 'terro' },
  'makan': { high: 'neddha', low: 'ngakan' },
  'nasi': { high: 'nase\'', low: 'nase\'' },
  'minum': { high: 'ngonjhung', low: 'ngenom' },
  'tidur': { high: 'asera', low: 'tedhung' },
  'pergi': { high: 'alomampah', low: 'entar' },
  'ke': { high: 'ka', low: 'ka' },
  'mana': { high: 'dhimma', low: 'dhimma' },
  'sini': { high: 'enna\'', low: 'enna\'' },
  'sana': { high: 'issa\'', low: 'issa\'' },
  'apa': { high: 'punapa', low: 'apa' },
  'siapa': { high: 'sinten', low: 'sapa' },
  'bagaimana': { high: 'kadospundi', low: 'de\'remmah' },
  'mengapa': { high: 'anapo', low: 'anapo' },
  'rumah': { high: 'dalem', low: 'roma' },
  'air': { high: 'toya', low: 'aeng' },
  'jalan': { high: 'ajalan', low: 'ajalan' },
  'sekarang': { high: 'sateya', low: 'sateya' },
  'tidak': { high: 'bhanten', low: 'enja\'' },
  'ya': { high: 'engghi', low: 'iya' },
  'baik': { high: 'sae', low: 'bagus' },
  'banyak': { high: 'banya\'', low: 'banya\'' },
  'sedikit': { high: 'sakone\'', low: 'sakone\'' },
  'besar': { high: 'ageng', low: 'raje' },
  'kecil': { high: 'alit', low: 'kene\'' },
  'tua': { high: 'sepuh', low: 'towa' },
  'sangat': { high: 'ongghu', low: 'ongghu' },
  'dari': { high: 'saking', low: 'dhari' },
  'dan': { high: 'sareng', low: 'ban' },
  'dengan': { high: 'sareng', low: 'ban' },
  'bisa': { high: 'saged', low: 'bisa' },
  'cara': { high: 'cara', low: 'cara' }
};

const WOTD_WORDS = [
  { word: 'Dhahar', spell: '/dha-har/', type: 'Jawa Krama', mean: 'Makan (digunakan untuk menghormati orang lain)', ex: '"Eyang nembe dhahar sekul goreng." (Kakek sedang makan nasi goreng.)' },
  { word: 'Neddha', spell: '/ned-dha/', type: 'Madura Formal', mean: 'Makan (digunakan untuk berkomunikasi formal/sopan)', ex: '"Bhiula terro neddha\'a nase\' goreng." (Saya ingin makan nasi goreng.)' },
  { word: 'Tindak', spell: '/tin-dak/', type: 'Jawa Krama', mean: 'Pergi (digunakan untuk menghormati orang lain)', ex: '"Bapak badhe tindak dhateng kantor." (Bapak akan pergi ke kantor.)' },
  { word: 'Alomampah', spell: '/a-lo-mam-pah/', type: 'Madura Formal', mean: 'Pergi (tingkat tutur halus Engghi-Bhanten)', ex: '"Panjhenengngan badhi alomampaha ka dhimma?" (Anda akan pergi ke mana?)' },
  { word: 'Sare', spell: '/sa-re/', type: 'Jawa Krama', mean: 'Tidur (digunakan untuk menghormati orang lain)', ex: '"Ibu nembe sare ing kamar wingking." (Ibu sedang tidur di kamar belakang.)' }
];

export default function LokalatorApp() {
  const [activePage, setActivePage] = useState<PageType>('landing');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [toastMsg, setToastMsg] = useState<{ text: string; icon: string } | null>(null);
  const [insightsData, setInsightsData] = useState<InsightsResult | null>(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [insightsRefreshKey, setInsightsRefreshKey] = useState(0);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window === 'undefined') return 'light';
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null;
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    return savedTheme === 'dark' || (!savedTheme && systemPrefersDark) ? 'dark' : 'light';
  });

  // Keep DOM theme class in sync with state.
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const toggleTheme = () => {
    if (theme === 'light') {
      setTheme('dark');
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
      triggerToast('Mode Gelap diaktifkan', 'moon');
    } else {
      setTheme('light');
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
      triggerToast('Mode Terang diaktifkan', 'sun');
    }
  };

  // --- TRANSLATOR STATE ---
  const [sourceLang, setSourceLang] = useState('id');
  const [targetLang, setTargetLang] = useState('jv');
  const [targetLevel, setTargetLevel] = useState<'low' | 'high'>('high'); // low = Ngoko/Enja-Iya, high = Krama/Engghi-Bhanten
  const [inputText, setInputText] = useState('');
  const [translatedText, setTranslatedText] = useState('');
  const [politenessAnalysis, setPolitenessAnalysis] = useState<{ ngoko: number; krama: number; summary: string }>({ ngoko: 0, krama: 0, summary: 'Belum ada analisis' });
  const [culturalContext, setCulturalContext] = useState('Masukkan teks untuk melihat konteks budaya.');
  const [suggestedVersion, setSuggestedVersion] = useState<string | null>(null);
  const [translationLoading, setTranslationLoading] = useState(false);
  const [translationStatus, setTranslationStatus] = useState('Siap.');
  const translationAbortRef = useRef<AbortController | null>(null);
  const translationRequestIdRef = useRef(0);

  // --- DOCUMENT STATE ---
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [docSourceLang, setDocSourceLang] = useState('id');
  const [docTargetLang, setDocTargetLang] = useState('jv');
  const [docTargetLevel, setDocTargetLevel] = useState<'low' | 'high'>('high');
  const [docProgress, setDocProgress] = useState(-1); // -1 = not started
  const [docProgressStep, setDocProgressStep] = useState('');
  const [docTranslatedName, setDocTranslatedName] = useState('');
  const [docDownloadUrl, setDocDownloadUrl] = useState('');
  const [docTranslatedText, setDocTranslatedText] = useState('');
  const [docPreviewTruncated, setDocPreviewTruncated] = useState(false);
  const [docWordsTranslated, setDocWordsTranslated] = useState(0);
  const [docPolitenessSummary, setDocPolitenessSummary] = useState('');
  const [docError, setDocError] = useState('');
  const [docDownloading, setDocDownloading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- WORD OF THE DAY STATE ---
  const [wotdIndex, setWotdIndex] = useState(0);

  // --- DETECTOR STATE ---
  const [detectorInput, setDetectorInput] = useState('');
  const [detectorResult, setDetectorResult] = useState<{
    language: string;
    register: string;
    explanation: string;
    ngokoPercentage?: number;
    kramaPercentage?: number;
    wordAnalysis?: { word: string; language: string; level: string }[];
  } | null>(null);
  const [loadingDetect, setLoadingDetect] = useState(false);

  // --- CHATBOT STATE ---
  const [chatMessages, setChatMessages] = useState<{ role: string; text: string }[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatWidgetOpen, setChatWidgetOpen] = useState(false);
  const [chatExpanded, setChatExpanded] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto cycle word of the day
  useEffect(() => {
    const timer = setInterval(() => {
      setWotdIndex((prev) => (prev + 1) % WOTD_WORDS.length);
    }, 15000);
    return () => clearInterval(timer);
  }, []);

  // Show Toast Notifier
  const triggerToast = (text: string, icon = 'info') => {
    setToastMsg({ text, icon });
    setTimeout(() => setToastMsg(null), 3000);
  };

  const formatMetric = (value: number) => new Intl.NumberFormat('id-ID').format(value);
  const formatSearchCount = (value: number) => `${formatMetric(value)} pencarian`;

  const fetchInsights = useCallback(async (signal?: AbortSignal) => {
    setInsightsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/insights`, { signal });
      if (!response.ok) throw new Error('Failed to load insights');
      const data = await response.json() as InsightsResult;
      setInsightsData(data);
    } catch {
      if (!signal?.aborted) setInsightsData(null);
    } finally {
      if (!signal?.aborted) setInsightsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activePage !== 'insights') return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void fetchInsights(controller.signal);
    }, 0);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [activePage, fetchInsights, insightsRefreshKey]);

  // --- DETECTOR ACTION LOGIC ---
  const performOfflineDetection = (text: string) => {
    const clean = text.toLowerCase().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g, "").trim();
    const words = clean.split(/\s+/);
    if (!words.length || words[0] === '') {
      return {
        language: 'Tidak pasti',
        register: 'tidak diketahui',
        explanation: 'Teks kosong.',
        ngokoPercentage: 0,
        kramaPercentage: 0,
        wordAnalysis: []
      };
    }

    const jvNgokoCore = new Set(['aku', 'kowe', 'arep', 'ora', 'sing', 'opo', 'sopo', 'piye', 'kene', 'kono', 'neng', 'karo', 'lan', 'dadi']);
    const jvKramaCore = new Set(['kula', 'badhe', 'mboten', 'ingkang', 'punapa', 'sinten', 'kadospundi', 'mriki', 'mrika', 'dhateng', 'kaliyan', 'dados', 'panjenengan', 'sampeyan']);
    const jvInggilVerbs = new Set(['dhahar', 'sare', 'tindak', 'rawuh', 'sowan', 'kersa', 'nampi', 'jumeneng', 'dalem', 'sugeng']);
    const jvKasar = new Set(['jancok', 'jancuk', 'dancok', 'cuk', 'asu', 'bajingan', 'raimu', 'ndasmu', 'matamu', 'picek']);

    const madEnjaIyaCore = new Set(["sengko'", "engko'", "ba'na", "ba'en", "terro", "ngakan", "ngakana", "nase", "nase'", "enja'"]);
    const madEngghiEntenCore = new Set(["bula", "bula'", "dhika", "dhiko", "ka", "dhimma", "sampeyan"]);
    const madEngghiBhuntenCore = new Set(["kaula", "kaula'", "bhâdhân", "panjhenengngan", "badhi", "alomampah", "alomampaha", "engghi", "bhanten", "bhunten", "ajunan", "srèra"]);
    const indoStandard = new Set(['saya', 'mau', 'makan', 'tidur', 'tidak', 'sudah', 'sedang', 'sangat', 'di', 'warung']);
    const indoSlang = new Set(['gue', 'gua', 'lu', 'nggak', 'aja', 'udah', 'lagi', 'kenapa', 'banget', 'pengen', 'bobo', 'mager', 'bodo']);

    const wordAnalysis = words.map(word => {
      if (word.length <= 1) return { word, language: 'Tidak pasti', level: 'tidak dikenal' };
      if (jvKasar.has(word)) return { word, language: 'Jawa', level: 'ngoko kasar' };
      if (jvKramaCore.has(word) || jvInggilVerbs.has(word)) return { word, language: 'Jawa', level: 'krama' };
      if (jvNgokoCore.has(word)) return { word, language: 'Jawa', level: 'ngoko' };
      if (madEngghiBhuntenCore.has(word)) return { word, language: 'Madura', level: 'engghi-bhunten' };
      if (madEngghiEntenCore.has(word)) return { word, language: 'Madura', level: 'engghi-enten' };
      if (madEnjaIyaCore.has(word)) return { word, language: 'Madura', level: 'enja-iya' };
      if (indoSlang.has(word)) return { word, language: 'Indonesia', level: 'informal' };
      if (indoStandard.has(word)) return { word, language: 'Indonesia', level: 'netral' };
      return { word, language: 'Tidak pasti', level: 'tidak dikenal' };
    });

    const languageCounts = wordAnalysis.reduce<Record<string, number>>((counts, item) => {
      if (item.language === 'Indonesia' || item.language === 'Jawa' || item.language === 'Madura') {
        counts[item.language] += 1;
      }
      return counts;
    }, { Indonesia: 0, Jawa: 0, Madura: 0 });
    const topCount = Math.max(languageCounts.Indonesia, languageCounts.Jawa, languageCounts.Madura);
    const topLanguages = Object.entries(languageCounts)
      .filter(([, count]) => count === topCount)
      .map(([language]) => language);
    const topPercentage = Math.round((topCount / words.length) * 1000) / 10;
    const minLanguagePercentage = 50;

    if (topCount === 0) {
      return {
        language: 'Tidak pasti',
        register: 'tidak diketahui',
        explanation: 'Tidak ada kosakata yang cocok dengan indikator lokal. Sistem tidak memaksa hasil ke Indonesia formal saat bukti tidak cukup.',
        ngokoPercentage: 0,
        kramaPercentage: 0,
        wordAnalysis
      };
    }

    if (topLanguages.length > 1) {
      return {
        language: 'Tidak pasti',
        register: 'ambigu',
        explanation: 'Persentase indikator bahasa seimbang, sehingga sistem tidak cukup yakin untuk memilih satu bahasa.',
        ngokoPercentage: 50,
        kramaPercentage: 50,
        wordAnalysis
      };
    }

    if (topPercentage < minLanguagePercentage) {
      return {
        language: 'Tidak pasti',
        register: 'tidak diketahui',
        explanation: `Hanya ${topPercentage}% token yang cocok dengan indikator ${topLanguages[0]}; bukti belum cukup untuk menetapkan bahasa keseluruhan.`,
        ngokoPercentage: 0,
        kramaPercentage: 0,
        wordAnalysis
      };
    }

    const lang = topLanguages[0];

    if (lang === 'Indonesia') {
      const matchedSlang = words.filter(w => indoSlang.has(w));
      if (matchedSlang.length > 0) {
        return {
          language: 'Indonesia',
          register: 'informal',
          explanation: `Teks dideteksi sebagai Bahasa Indonesia informal karena menggunakan kosakata gaul/slang: ${matchedSlang.join(', ')}.`,
          ngokoPercentage: 0,
          kramaPercentage: 0,
          wordAnalysis
        };
      }
      return {
        language: 'Indonesia',
        register: 'formal',
        explanation: 'Teks menggunakan Bahasa Indonesia formal dengan kosakata baku.',
        ngokoPercentage: 0,
        kramaPercentage: 0,
        wordAnalysis
      };
    } else if (lang === 'Jawa') {
      const hasNgokoCore = words.some(w => jvNgokoCore.has(w)) || words.includes('kowe') || words.includes('aku');
      const hasKramaCore = words.some(w => jvKramaCore.has(w)) || words.includes('kula');
      const hasInggil = words.some(w => jvInggilVerbs.has(w));
      const kasarWords = words.filter(w => jvKasar.has(w));

      if (kasarWords.length > 0) {
        return {
          language: 'Jawa',
          register: 'ngoko kasar',
          explanation: `Teks memuat ekspresi Jawa sangat informal/kasar: ${kasarWords.join(', ')}.`,
          ngokoPercentage: 98,
          kramaPercentage: 2,
          wordAnalysis
        };
      } else if (hasKramaCore) {
        if (hasInggil) {
          return {
            language: 'Jawa',
            register: 'krama alus',
            explanation: 'Teks menggunakan ragam Jawa Krama Alus (formal/sangat sopan) karena menggunakan kata ganti/partikel Krama serta verba penghormatan Krama Inggil.',
            ngokoPercentage: 15,
            kramaPercentage: 85,
            wordAnalysis
          };
        }
        return {
          language: 'Jawa',
          register: 'krama lugu',
          explanation: 'Teks menggunakan ragam Jawa Krama Lugu (formal/menengah) karena menggunakan kosakata Krama Lugu tanpa campuran verba Krama Inggil.',
          ngokoPercentage: 20,
          kramaPercentage: 80,
          wordAnalysis
        };
      } else if (hasNgokoCore) {
        if (hasInggil) {
          return {
            language: 'Jawa',
            register: 'ngoko alus',
            explanation: 'Teks menggunakan ragam Jawa Ngoko Alus karena memadukan kerangka kata Ngoko dengan kata penghormatan Krama Inggil untuk menghormati mitra tutur.',
            ngokoPercentage: 55,
            kramaPercentage: 45,
            wordAnalysis
          };
        }
        return {
          language: 'Jawa',
          register: 'ngoko lugu',
          explanation: 'Teks menggunakan ragam Jawa Ngoko Lugu (kasual sehari-hari) dengan kosakata informal.',
          ngokoPercentage: 85,
          kramaPercentage: 15,
          wordAnalysis
        };
      }
      return {
        language: 'Jawa',
        register: 'ngoko lugu',
        explanation: 'Teks menggunakan ragam Jawa Ngoko Lugu.',
        ngokoPercentage: 85,
        kramaPercentage: 15,
        wordAnalysis
      };
    } else {
      const hasEnjaIya = words.some(w => madEnjaIyaCore.has(w));
      const hasEngghiEnten = words.some(w => madEngghiEntenCore.has(w));
      const hasEngghiBhunten = words.some(w => madEngghiBhuntenCore.has(w));

      if (hasEngghiBhunten) {
        return {
          language: 'Madura',
          register: 'Engghi-bhunten',
          explanation: 'Teks menggunakan ragam Madura Engghi-bhunten (tingkat tutur halus/formal).',
          ngokoPercentage: 15,
          kramaPercentage: 85,
          wordAnalysis
        };
      } else if (hasEngghiEnten) {
        return {
          language: 'Madura',
          register: 'Engghi-enten',
          explanation: 'Teks menggunakan ragam Madura Engghi-enten (tingkat tutur menengah).',
          ngokoPercentage: 45,
          kramaPercentage: 55,
          wordAnalysis
        };
      }
      return {
        language: 'Madura',
        register: 'Enja-Iya',
        explanation: hasEnjaIya
          ? 'Teks menggunakan ragam Madura Enja-Iya (tingkat tutur kasual sehari-hari).'
          : 'Teks cenderung menggunakan ragam Madura Enja-Iya berdasarkan kosakata yang tersedia.',
        ngokoPercentage: 85,
        kramaPercentage: 15,
        wordAnalysis
      };
    }
  };

  const handleDetectRegister = async () => {
    if (!detectorInput.trim()) return;
    setLoadingDetect(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/detect-register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: detectorInput })
      });
      if (response.ok) {
        const data = await response.json();
        setDetectorResult(data);
        triggerToast('Teks berhasil dianalisis!', 'check');
      } else {
        throw new Error('Server returned error');
      }
    } catch {
      const result = performOfflineDetection(detectorInput);
      setDetectorResult(result);
      triggerToast('Analisis selesai (Offline Mode)', 'info');
    } finally {
      setLoadingDetect(false);
    }
  };

  // --- CHATBOT LOGIC ---
  const handleSendChat = async () => {
    if (!chatInput.trim() || chatLoading) return;
    const userMsg = { role: 'user', text: chatInput };
    setChatMessages(prev => [...prev, userMsg]);
    setChatInput('');
    setChatLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg.text,
          history: chatMessages.slice(-10)
        })
      });
      if (response.ok) {
        const data = await response.json();
        setChatMessages(prev => [...prev, { role: 'assistant', text: data.response }]);
      } else {
        const err = await response.json().catch(() => ({ detail: 'Chatbot tidak tersedia.' }));
        setChatMessages(prev => [...prev, { role: 'assistant', text: `⚠️ ${err.detail || 'Terjadi kesalahan.'}` }]);
      }
    } catch {
      setChatMessages(prev => [...prev, { role: 'assistant', text: '⚠️ Tidak dapat terhubung ke server. Pastikan backend berjalan.' }]);
    } finally {
      setChatLoading(false);
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    }
  };

  useEffect(() => {
    if (!chatWidgetOpen) return;
    const timer = window.setTimeout(() => {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
    return () => window.clearTimeout(timer);
  }, [chatWidgetOpen, chatExpanded, chatMessages.length]);

  // Switch hash route support
  useEffect(() => {
    const handleHash = () => {
      const hash = window.location.hash;
      if (hash === '#beranda') setActivePage('landing');
      else if (hash === '#penerjemah') setActivePage('translator');
      else if (hash === '#dokumen') setActivePage('doc-translator');
      else if (hash === '#deteksi') setActivePage('detector');
      else if (hash === '#chatbot') {
        setActivePage('landing');
        setChatWidgetOpen(true);
      }
      else if (hash === '#analitik-bahasa' || hash === '#statistik') setActivePage('insights');
      else if (hash === '#tentang') setActivePage('about');
      else if (hash === '#kebijakan-privasi') setActivePage('privacy');
      else if (hash === '#syarat-ketentuan') setActivePage('terms');
    };
    window.addEventListener('hashchange', handleHash);
    handleHash();
    return () => window.removeEventListener('hashchange', handleHash);
  }, []);

  // Sync state pages
  const handleNavigate = (page: PageType) => {
    setActivePage(page);
    setMobileMenuOpen(false);
    // update hash
    const hashes: Record<PageType, string> = {
      landing: '#beranda',
      translator: '#penerjemah',
      'doc-translator': '#dokumen',
      detector: '#deteksi',
      insights: '#analitik-bahasa',
      about: '#tentang',
      privacy: '#kebijakan-privasi',
      terms: '#syarat-ketentuan'
    };
    window.location.hash = hashes[page];
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // --- OFFLINE/FALLBACK TRANSLATOR LOGIC ---
  const performOfflineTranslation = useCallback((text: string, src: string, target: string, level: 'low' | 'high'): TranslationResult => {
    const clean = text.toLowerCase().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g, "").trim();
    const key = `${src}_${target}`;

    // 1. Direct Phrase Match
    if (LOCAL_PHRASES[key] && LOCAL_PHRASES[key][clean]) {
      const phrase = LOCAL_PHRASES[key][clean];
      const selectedText = level === 'high' ? phrase.high : phrase.low;
      const alternativeText = level === 'high' ? phrase.low : phrase.high;
      return {
        translatedText: selectedText,
        politenessLevel: target === 'jv' ? (level === 'high' ? 'Krama Alus' : 'Ngoko Lugu') : (level === 'high' ? 'Engghi-Bhanten' : 'Enja-Iya'),
        ngokoPercentage: level === 'high' ? 10 : 90,
        kramaPercentage: level === 'high' ? 90 : 10,
        context: phrase.context,
        alternativeText: alternativeText
      };
    }

    // 2. Word-by-word Translation
    const dict = target === 'jv' ? ID_TO_JV_WORDS : ID_TO_MAD_WORDS;
    const words = text.split(/\s+/);
    const altLevel = level === 'high' ? 'low' : 'high';
    const applyCase = (source: string, replacement: string) =>
      source[0] === source[0]?.toUpperCase()
        ? replacement.charAt(0).toUpperCase() + replacement.slice(1)
        : replacement;
    const dedupeBeforeSuffix = (token: string, suffix: string) => {
      if (!token.endsWith(suffix)) return null;
      const stem = token.slice(0, -suffix.length);
      return stem.length >= 2 && stem[stem.length - 1] === stem[stem.length - 2]
        ? `${stem.slice(0, -1)}${suffix}`
        : null;
    };
    const jvPossessive = (value: string, selectedLevel: 'low' | 'high') => {
      if (selectedLevel === 'high') return `${value}${/[aiueo]$/i.test(value) ? 'nipun' : 'ipun'}`;
      return `${value}${/[aiueo]$/i.test(value) ? 'ne' : 'e'}`;
    };
    const jvCausative = (value: string, selectedLevel: 'low' | 'high') => {
      if (selectedLevel === 'high') return `${value}aken`;
      return value.endsWith('u') ? `${value.slice(0, -1)}okno` : `${value}no`;
    };
    const jvPassive = (baseToken: string, value: string, selectedLevel: 'low' | 'high') => {
      if (baseToken === 'makan') return selectedLevel === 'high' ? 'dipundhahar' : 'dipangan';
      return selectedLevel === 'high' ? `dipun${value}` : `di${value}`;
    };
    const jvLocativeCompound = (token: string, selectedLevel: 'low' | 'high') => {
      if (!token.startsWith('di')) return null;
      const base = token.slice(2);
      if (base !== 'jalan') return null;
      return selectedLevel === 'high' ? 'wonten margi' : 'neng dalan';
    };
    const translateCore = (core: string, selectedLevel: 'low' | 'high'): string | null => {
      const candidates = [core];
      ['nya', 'kan', 'kannya'].forEach(suffix => {
        const normalized = dedupeBeforeSuffix(core, suffix);
        if (normalized && !candidates.includes(normalized)) candidates.push(normalized);
      });

      for (const candidate of candidates) {
        if (dict[candidate]) return dict[candidate][selectedLevel];
        if (target !== 'jv') continue;

        if (candidate.includes('-')) {
          const parts = candidate.split('-');
          if (parts.length === 2 && parts[0] === parts[1] && parts[0]) {
            const repeated = translateCore(parts[0], selectedLevel);
            if (repeated) return `${repeated}-${repeated}`;
          }
        }

        const locative = jvLocativeCompound(candidate, selectedLevel);
        if (locative) return locative;

        if (candidate.startsWith('di') && candidate.length > 2) {
          const base = candidate.slice(2);
          const translatedBase = translateCore(base, selectedLevel);
          if (translatedBase) return jvPassive(base, translatedBase, selectedLevel);
        }

        if (candidate.endsWith('nya') && candidate.length > 3) {
          const base = translateCore(candidate.slice(0, -3), selectedLevel);
          if (base) return jvPossessive(base, selectedLevel);
        }

        if (candidate.endsWith('kan') && candidate.length > 3) {
          const derived = [`men${candidate}`, `me${candidate}`].find(item => dict[item]);
          if (derived) return dict[derived][selectedLevel];

          const base = candidate.slice(0, -3);
          if (dict[base]) return jvCausative(dict[base][selectedLevel], selectedLevel);
        }

        if (candidate.startsWith('memper') && candidate.endsWith('kan')) {
          const base = candidate.slice(6, -3);
          if (dict[base]) return jvCausative(dict[base][selectedLevel], selectedLevel);
        }
      }
      return null;
    };
    const translateToken = (word: string, selectedLevel: 'low' | 'high') => {
      const match = word.match(/^([^\w']*)([\w'\-̀-ỹ]+)([^\w']*)$/u);
      if (!match) return word;
      const [, prefix, core, suffix] = match;
      const translatedCore = translateCore(core.toLowerCase(), selectedLevel);
      return translatedCore ? `${prefix}${applyCase(core, translatedCore)}${suffix}` : word;
    };
    const translated = words.map(word => {
      return translateToken(word, level);
    });

    const isHigh = level === 'high';
    const computedText = translated.join(' ');

    // Generate context descriptions
    let context = '';
    if (target === 'jv') {
      context = isHigh
        ? 'Tingkat Krama Alus digunakan untuk berbicara dengan orang yang dihormati, orang tua, atau atasan.'
        : 'Tingkat Ngoko Lugu digunakan untuk berbicara kepada teman sebaya, kerabat dekat, atau orang yang lebih muda.';
    } else {
      context = isHigh
        ? 'Tingkat tutur Engghi-Bhanten mencerminkan sopan santun dan rasa hormat yang tinggi kepada lawan tutur.'
        : 'Tingkat tutur Enja-Iya digunakan dalam percakapan kasual sehari-hari dengan kawan karib.';
    }

    // Get alternatives
    const altTranslated = words.map(word => {
      return translateToken(word, altLevel);
    }).join(' ');

    return {
      translatedText: computedText,
      politenessLevel: target === 'jv' ? (isHigh ? 'Krama Alus' : 'Ngoko Lugu') : (isHigh ? 'Engghi-Bhanten' : 'Enja-Iya'),
      ngokoPercentage: isHigh ? 15 : 85,
      kramaPercentage: isHigh ? 85 : 15,
      context: context,
      alternativeText: altTranslated !== computedText ? altTranslated : undefined
    };
  }, []);

  // Live text translation uses the backend API first; local translation is a silent fallback.
  const handleTranslate = useCallback(async (textVal: string) => {
    if (!textVal.trim()) {
      translationAbortRef.current?.abort();
      translationRequestIdRef.current += 1;
      setTranslationLoading(false);
      setTranslatedText('');
      setPolitenessAnalysis({ ngoko: 0, krama: 0, summary: 'Belum ada analisis' });
      setCulturalContext('Masukkan teks untuk melihat konteks budaya.');
      setSuggestedVersion(null);
      setTranslationStatus('Siap.');
      return;
    }

    translationAbortRef.current?.abort();
    const controller = new AbortController();
    translationAbortRef.current = controller;
    const requestId = translationRequestIdRef.current + 1;
    translationRequestIdRef.current = requestId;
    const timeoutId = window.setTimeout(() => controller.abort(), 30000);

    setTranslationLoading(true);
    setTranslationStatus('Menerjemahkan...');

    try {
      const response = await fetch(`${API_BASE_URL}/api/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          text: textVal,
          source_lang: sourceLang,
          target_lang: targetLang,
          level: targetLevel,
          use_ai: true
        })
      });

      if (requestId !== translationRequestIdRef.current) return;

      if (response.ok) {
        const data = await response.json() as TranslationResult;
        setTranslatedText(data.translatedText);
        setPolitenessAnalysis({
          ngoko: data.ngokoPercentage,
          krama: data.kramaPercentage,
          summary: `Tingkat tutur terdeteksi: ${data.politenessLevel}`
        });
        setCulturalContext(data.context);
        setSuggestedVersion(data.alternativeText || null);
        const providerLabel = data.translationProvider === 'gemini'
          ? 'Gemini'
          : data.translationProvider === 'google_translate'
            ? 'Google Translate'
            : data.translationProvider === 'cache'
              ? 'cache API'
              : 'fallback lokal';
        setTranslationStatus(data.usedFallback
          ? 'Hasil fallback lokal.'
          : `Terjemahan konteks via ${providerLabel}.`);
        setInsightsRefreshKey((value) => value + 1);
      } else {
        throw new Error('Server translation failed');
      }
    } catch {
      if (requestId !== translationRequestIdRef.current) return;
      const offlineResult = performOfflineTranslation(textVal, sourceLang, targetLang, targetLevel);
      setTranslatedText(offlineResult.translatedText);
      setPolitenessAnalysis({
        ngoko: offlineResult.ngokoPercentage,
        krama: offlineResult.kramaPercentage,
        summary: `Tingkat tutur terdeteksi: ${offlineResult.politenessLevel}`
      });
      setCulturalContext(offlineResult.context);
      setSuggestedVersion(offlineResult.alternativeText || null);
      setTranslationStatus('Hasil fallback lokal.');
      setInsightsRefreshKey((value) => value + 1);
    } finally {
      window.clearTimeout(timeoutId);
      if (requestId === translationRequestIdRef.current) {
        setTranslationLoading(false);
      }
    }
  }, [
    sourceLang,
    targetLang,
    targetLevel,
    performOfflineTranslation,
    setTranslationLoading,
    setTranslationStatus,
    setTranslatedText,
    setPolitenessAnalysis,
    setCulturalContext,
    setSuggestedVersion
  ]);

  // Handle change in input text
  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      handleTranslate(inputText);
    }, 650);
    return () => clearTimeout(delayDebounce);
  }, [inputText, handleTranslate]);

  // Swap Languages
  const handleSwapLanguages = () => {
    if (sourceLang === 'id' && targetLang === 'id') return;
    const temp = sourceLang;
    setSourceLang(targetLang);
    setTargetLang(temp);
    setInputText(translatedText);
    triggerToast('Bahasa ditukar', 'refresh-cw');
  };

  // Copy Clipboard
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      triggerToast('Teks disalin ke clipboard', 'check');
    }).catch(() => {
      triggerToast('Gagal menyalin teks', 'x');
    });
  };

  // --- DOCUMENT ZONE ---
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processDocumentFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processDocumentFile(e.target.files[0]);
    }
  };

  const processDocumentFile = (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'pdf' && ext !== 'docx' && ext !== 'doc' && ext !== 'txt') {
      triggerToast('Hanya mendukung file PDF, DOCX, DOC, atau TXT!', 'alert-circle');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      triggerToast('Ukuran maksimal dokumen adalah 10MB.', 'alert-circle');
      return;
    }
    setUploadedFile(file);
    setDocProgress(-1);
    setDocTranslatedName('');
    setDocDownloadUrl('');
    setDocTranslatedText('');
    setDocPreviewTruncated(false);
    setDocWordsTranslated(0);
    setDocPolitenessSummary('');
    setDocError('');
    triggerToast('Dokumen berhasil diunggah', 'check');
  };

  const clearDocument = () => {
    setUploadedFile(null);
    setDocProgress(-1);
    setDocProgressStep('');
    setDocTranslatedName('');
    setDocDownloadUrl('');
    setDocTranslatedText('');
    setDocPreviewTruncated(false);
    setDocWordsTranslated(0);
    setDocPolitenessSummary('');
    setDocError('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const startDocumentTranslation = async () => {
    if (!uploadedFile) return;

    setDocProgress(0);
    setDocProgressStep('Mengunggah dan memvalidasi dokumen...');
    setDocError('');
    setDocTranslatedText('');
    setDocDownloadUrl('');

    const formData = new FormData();
    formData.append('file', uploadedFile);
    formData.append('source_lang', docSourceLang);
    formData.append('target_lang', docTargetLang);
    formData.append('level', docTargetLevel);

    try {
      setDocProgress(35);
      setDocProgressStep('Mengekstrak teks dan menjalankan pipeline terjemahan...');
      const response = await fetch(`${API_BASE_URL}/api/translate-document`, {
        method: 'POST',
        body: formData
      });

      setDocProgress(75);
      setDocProgressStep('Menyusun hasil terjemahan...');

      if (!response.ok) {
        let message = 'Dokumen gagal diterjemahkan.';
        try {
          const errorBody = await response.json();
          message = errorBody.detail || message;
        } catch {
          // Keep default message when the API did not send JSON.
        }
        throw new Error(message);
      }

      const data = await response.json() as DocumentTranslationResult;
      setDocTranslatedName(data.filename);
      setDocDownloadUrl(data.downloadUrl);
      setDocTranslatedText(data.translatedText);
      setDocPreviewTruncated(data.previewTruncated);
      setDocWordsTranslated(data.wordsTranslated);
      setDocPolitenessSummary(data.politenessSummary);
      setDocProgress(100);
      setDocProgressStep('Penerjemahan selesai.');
      setInsightsRefreshKey((value) => value + 1);
      triggerToast('Dokumen berhasil diterjemahkan!', 'check');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Dokumen gagal diterjemahkan.';
      setDocProgress(-1);
      setDocError(message);
      triggerToast(message, 'alert-circle');
    }
  };

  const downloadTranslatedDocument = async () => {
    if (!docTranslatedName || !docDownloadUrl) return;

    setDocDownloading(true);
    try {
      const response = await fetch(`${API_BASE_URL}${docDownloadUrl}`);
      if (!response.ok) throw new Error('Berkas hasil sudah kedaluwarsa atau tidak tersedia.');
      const blob = await response.blob();
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = docTranslatedName;
      document.body.appendChild(link);
      link.click();
      URL.revokeObjectURL(link.href);
      document.body.removeChild(link);
      setDocDownloadUrl('');
      triggerToast('Unduhan berkas dimulai!', 'download');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Gagal mengunduh berkas.';
      triggerToast(message, 'alert-circle');
    } finally {
      setDocDownloading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen text-text-dark font-sans relative antialiased">

      {/* Navigation Bar */}
      <nav className="sticky top-0 z-50 bg-bg-cream/90 backdrop-blur-md border-b border-border-color px-6 py-4 grid grid-cols-[1fr_auto] md:grid-cols-[1fr_auto_1fr] items-center gap-6 smooth-transition">
        <div className="flex items-center gap-3 cursor-pointer justify-self-start" onClick={() => handleNavigate('landing')}>
          <div className="h-[54px] w-[54px] rounded-lg flex items-center justify-center shadow-md overflow-hidden bg-white">
            <Image
              src="/assets/lokalator_logo_centered.png"
              alt="Logo Lokalator"
              width={54}
              height={54}
              className="brand-logo h-full w-full scale-90 object-contain"
            />
          </div>
          <span className="font-heading font-bold text-xl text-primary">
            Lokalator
          </span>
        </div>

        {/* Desktop Menu */}
        <ul className="hidden md:flex items-center justify-center gap-8 list-none justify-self-center">
          <li className={`relative font-semibold text-sm cursor-pointer smooth-transition ${activePage === 'landing' ? 'text-primary' : 'text-text-medium hover:text-primary'}`} onClick={() => handleNavigate('landing')}>
            Beranda
            {activePage === 'landing' && <div className="absolute -bottom-1 left-0 right-0 h-[2px] bg-accent-gold" />}
          </li>
          <li className={`relative font-semibold text-sm cursor-pointer smooth-transition ${activePage === 'translator' ? 'text-primary' : 'text-text-medium hover:text-primary'}`} onClick={() => handleNavigate('translator')}>
            Penerjemah
            {activePage === 'translator' && <div className="absolute -bottom-1 left-0 right-0 h-[2px] bg-accent-gold" />}
          </li>
          <li className={`relative font-semibold text-sm cursor-pointer smooth-transition ${activePage === 'doc-translator' ? 'text-primary' : 'text-text-medium hover:text-primary'}`} onClick={() => handleNavigate('doc-translator')}>
            Terjemah Dokumen
            {activePage === 'doc-translator' && <div className="absolute -bottom-1 left-0 right-0 h-[2px] bg-accent-gold" />}
          </li>
          <li className={`relative font-semibold text-sm cursor-pointer smooth-transition ${activePage === 'detector' ? 'text-primary' : 'text-text-medium hover:text-primary'}`} onClick={() => handleNavigate('detector')}>
            Deteksi Kesopanan
            {activePage === 'detector' && <div className="absolute -bottom-1 left-0 right-0 h-[2px] bg-accent-gold" />}
          </li>
          <li className={`relative font-semibold text-sm cursor-pointer smooth-transition ${activePage === 'insights' ? 'text-primary' : 'text-text-medium hover:text-primary'}`} onClick={() => handleNavigate('insights')}>
            Analitik Bahasa
            {activePage === 'insights' && <div className="absolute -bottom-1 left-0 right-0 h-[2px] bg-accent-gold" />}
          </li>
          <li className={`relative font-semibold text-sm cursor-pointer smooth-transition ${activePage === 'about' ? 'text-primary' : 'text-text-medium hover:text-primary'}`} onClick={() => handleNavigate('about')}>
            Tentang
            {activePage === 'about' && <div className="absolute -bottom-1 left-0 right-0 h-[2px] bg-accent-gold" />}
          </li>
        </ul>

        <div className="hidden md:flex items-center justify-end gap-5 justify-self-end">
          <button onClick={toggleTheme} className="text-text-medium hover:text-primary p-2 rounded-lg hover:bg-neutral-light cursor-pointer smooth-transition" title="Ubah Tema">
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>
          <button className="bg-primary hover:bg-primary-light text-white font-semibold px-6 py-3 rounded-xl flex items-center gap-2 shadow-md hover:-translate-y-0.5 smooth-transition cursor-pointer" onClick={() => handleNavigate('translator')}>
            Mulai Sekarang
          </button>
        </div>

        {/* Mobile menu toggle */}
        <button className="block md:hidden text-primary p-1 cursor-pointer justify-self-end" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>

        {/* Mobile Menu Panel */}
        {mobileMenuOpen && (
          <div className="absolute top-full left-0 right-0 bg-card-bg border-b border-border-color shadow-lg p-6 flex flex-col gap-4 md:hidden animation-fadeIn">
            <div className="py-2 border-b border-neutral-light font-semibold text-sm text-text-medium" onClick={() => handleNavigate('landing')}>Beranda</div>
            <div className="py-2 border-b border-neutral-light font-semibold text-sm text-text-medium" onClick={() => handleNavigate('translator')}>Penerjemah</div>
            <div className="py-2 border-b border-neutral-light font-semibold text-sm text-text-medium" onClick={() => handleNavigate('doc-translator')}>Terjemah Dokumen</div>
            <div className="py-2 border-b border-neutral-light font-semibold text-sm text-text-medium" onClick={() => handleNavigate('detector')}>Deteksi Kesopanan</div>
            <div className="py-2 border-b border-neutral-light font-semibold text-sm text-text-medium" onClick={() => handleNavigate('insights')}>Analitik Bahasa</div>
            <div className="py-2 border-b border-neutral-light font-semibold text-sm text-text-medium" onClick={() => handleNavigate('about')}>Tentang</div>
            <button onClick={toggleTheme} className="flex items-center justify-center gap-2 border border-border-color py-2.5 rounded-lg text-text-medium font-semibold text-sm w-full cursor-pointer smooth-transition hover:bg-neutral-light">
              {theme === 'light' ? <><Moon size={16} /> Mode Gelap</> : <><Sun size={16} /> Mode Terang</>}
            </button>
            <button className="bg-primary text-white font-semibold text-sm py-2.5 rounded-lg w-full mt-2" onClick={() => handleNavigate('translator')}>
              Mulai Sekarang
            </button>
          </div>
        )}
      </nav>

      {/* LANDING PAGE VIEW */}
      {activePage === 'landing' && (
        <main className="flex-1">
          {/* Hero Section */}
          <section className="max-w-4xl mx-auto text-center px-6 pt-16 pb-12 flex flex-col items-center">
            <div className="mb-6 h-[270px] w-[270px] md:h-[330px] md:w-[330px]">
              <Image
                src="/assets/lokalator_logo_and_name.png"
                alt="Lokalator"
                width={330}
                height={330}
                priority
                className="brand-logo h-full w-full object-contain"
              />
            </div>
            <h1 className="font-heading font-extrabold text-4xl md:text-5xl leading-tight mb-6 bg-gradient-to-br from-primary to-accent-brown bg-clip-text text-transparent">
              Melestarikan Bahasa Daerah dengan Teknologi Modern
            </h1>
            <p className="text-text-medium text-base md:text-lg max-w-2xl mb-8 leading-relaxed">
              Platform AI untuk menerjemahkan Bahasa Indonesia, Jawa, dan Madura sekaligus menganalisis tingkat kesopanan bahasa secara real-time.
            </p>
            <div className="flex gap-4">
              <button className="bg-primary hover:bg-primary-light text-white font-semibold px-6 py-3 rounded-xl flex items-center gap-2 shadow-md hover:-translate-y-0.5 smooth-transition cursor-pointer" onClick={() => handleNavigate('translator')}>
                Coba Terjemahkan <ChevronRight size={16} />
              </button>
              <button className="bg-transparent border border-accent-brown hover:bg-accent-brown/5 text-accent-brown font-semibold px-6 py-3 rounded-xl flex items-center gap-2 hover:-translate-y-0.5 smooth-transition cursor-pointer" onClick={() => handleNavigate('doc-translator')}>
                Upload Dokumen <FileText size={16} />
              </button>
            </div>
          </section>

          {/* Features Grid */}
          <section className="max-w-6xl mx-auto px-6 py-12">
            <div className="text-center mb-12">
              <span className="text-accent-brown font-bold text-xs uppercase tracking-widest block mb-2">Fitur Unggulan</span>
              <h2 className="font-heading font-bold text-3xl">Teknologi Preservasi Digital</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="bg-white border border-border-color rounded-2xl p-6 shadow-xs hover:shadow-md hover:-translate-y-0.5 smooth-transition">
                <div className="w-11 h-11 bg-primary-transparent border border-primary/5 rounded-xl flex items-center justify-center text-primary mb-5">
                  <Languages size={20} />
                </div>
                <h3 className="font-heading font-semibold text-lg text-primary mb-2">Penerjemah Kontekstual</h3>
                <p className="text-text-medium text-sm leading-relaxed">Menerjemahkan kata atau kalimat antar Bahasa Indonesia, Jawa (Ngoko & Krama), dan Madura secara presisi.</p>
              </div>

              <div className="bg-white border border-border-color rounded-2xl p-6 shadow-xs hover:shadow-md hover:-translate-y-0.5 smooth-transition">
                <div className="w-11 h-11 bg-primary-transparent border border-primary/5 rounded-xl flex items-center justify-center text-primary mb-5">
                  <TrendingUp size={20} />
                </div>
                <h3 className="font-heading font-semibold text-lg text-primary mb-2">Deteksi Kesopanan</h3>
                <p className="text-text-medium text-sm leading-relaxed">Menganalisis leksikon kosakata untuk mendeteksi level kesopanan (Ngoko/Krama atau Formal/Informal) kalimat input.</p>
              </div>

              <div className="bg-white border border-border-color rounded-2xl p-6 shadow-xs hover:shadow-md hover:-translate-y-0.5 smooth-transition">
                <div className="w-11 h-11 bg-primary-transparent border border-primary/5 rounded-xl flex items-center justify-center text-primary mb-5">
                  <FileText size={20} />
                </div>
                <h3 className="font-heading font-semibold text-lg text-primary mb-2">Ekstraksi Dokumen</h3>
                <p className="text-text-medium text-sm leading-relaxed">Mendukung unggahan berkas PDF, DOC, DOCX, dan TXT, memproses terjemah secara massal dengan format yang tetap rapi.</p>
              </div>

              <div className="bg-white border border-border-color rounded-2xl p-6 shadow-xs hover:shadow-md hover:-translate-y-0.5 smooth-transition">
                <div className="w-11 h-11 bg-primary-transparent border border-primary/5 rounded-xl flex items-center justify-center text-primary mb-5">
                  <BookOpen size={20} />
                </div>
                <h3 className="font-heading font-semibold text-lg text-primary mb-2">Statistik Budaya</h3>
                <p className="text-text-medium text-sm leading-relaxed">Menampilkan visualisasi statistik vitalitas penggunaan bahasa ibu di era modern per generasi.</p>
              </div>
            </div>
          </section>

          {/* How It Works */}
          <section className="max-w-6xl mx-auto px-6 py-12">
            <div className="bg-white border border-border-color rounded-3xl p-8 md:p-12 shadow-xs relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-[4px] bg-gradient-to-r from-primary via-accent-brown to-accent-gold" />
              <div className="text-center mb-12">
                <span className="text-accent-brown font-bold text-xs uppercase tracking-widest block mb-2">Alur Kerja</span>
                <h2 className="font-heading font-bold text-3xl">Bagaimana Lokalator Bekerja</h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
                <div className="relative">
                  <span className="font-heading font-extrabold text-5xl text-primary/14 dark:text-[#65B29A]/40 absolute -top-5 left-0 leading-none">01</span>
                  <h3 className="font-heading font-semibold text-lg text-primary mt-4 mb-2 relative z-10">Unggah Teks / Berkas</h3>
                  <p className="text-text-medium text-sm leading-relaxed">Ketik kalimat pada editor terjemahan online atau masukkan file PDF/DOCX/DOC/TXT ke dropzone dokumen.</p>
                </div>
                <div className="relative">
                  <span className="font-heading font-extrabold text-5xl text-primary/14 dark:text-[#65B29A]/40 absolute -top-5 left-0 leading-none">02</span>
                  <h3 className="font-heading font-semibold text-lg text-primary mt-4 mb-2 relative z-10">Analisis NLP Kontekstual</h3>
                  <p className="text-text-medium text-sm leading-relaxed">Model AI mengklasifikasi tingkat kesopanan leksikon bahasa daerah dan memproses struktur gramatikal.</p>
                </div>
                <div className="relative">
                  <span className="font-heading font-extrabold text-5xl text-primary/14 dark:text-[#65B29A]/40 absolute -top-5 left-0 leading-none">03</span>
                  <h3 className="font-heading font-semibold text-lg text-primary mt-4 mb-2 relative z-10">Unduh & Lihat Panduan</h3>
                  <p className="text-text-medium text-sm leading-relaxed">Dapatkan hasil terjemahan lengkap dengan visualisasi persentase kesopanan serta penjelasan etika budayanya.</p>
                </div>
              </div>
            </div>
          </section>

          {/* Statistics Cards */}
          <section className="max-w-6xl mx-auto px-6 py-12 mb-12">
            <div className="text-center mb-12">
              <span className="text-accent-brown font-bold text-xs uppercase tracking-widest block mb-2">Status Kebudayaan</span>
              <h2 className="font-heading font-bold text-3xl">Vitalitas & Preservasi Bahasa Ibu</h2>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="bg-primary/5 border border-primary/10 rounded-xl p-6 text-center hover:bg-white hover:border-primary/20 hover:shadow-md smooth-transition">
                <div className="font-heading font-extrabold text-4xl text-primary mb-2">80 Jt+</div>
                <div className="font-semibold text-sm text-text-dark mb-1">Penutur Bahasa Jawa</div>
                <div className="text-xs text-text-muted">Rumpun bahasa daerah penutur terbesar di Indonesia.</div>
              </div>
              <div className="bg-primary/5 border border-primary/10 rounded-xl p-6 text-center hover:bg-white hover:border-primary/20 hover:shadow-md smooth-transition">
                <div className="font-heading font-extrabold text-4xl text-primary mb-2">7.3 Jt+</div>
                <div className="font-semibold text-sm text-text-dark mb-1">Penutur Bahasa Madura</div>
                <div className="text-xs text-text-muted">Banyak dituturkan di Madura dan Tapal Kuda Jatim.</div>
              </div>
              <div className="bg-primary/5 border border-primary/10 rounded-xl p-6 text-center hover:bg-white hover:border-primary/20 hover:shadow-md smooth-transition">
                <div className="font-heading font-extrabold text-4xl text-primary mb-2">4 Kategori</div>
                <div className="font-semibold text-sm text-text-dark mb-1">Tingkat Kesopanan</div>
                <div className="text-xs text-text-muted">Deteksi linguistik: Ngoko, Krama, Formal, Informal.</div>
              </div>
              <div className="bg-primary/5 border border-primary/10 rounded-xl p-6 text-center hover:bg-white hover:border-primary/20 hover:shadow-md smooth-transition">
                <div className="font-heading font-extrabold text-4xl text-primary mb-2">98.2%</div>
                <div className="font-semibold text-sm text-text-dark mb-1">Akurasi Semantik</div>
                <div className="text-xs text-text-muted">Penilaian linguistik didukung kamus terverifikasi.</div>
              </div>
            </div>
          </section>
        </main>
      )}

      {/* TRANSLATOR PAGE VIEW */}
      {activePage === 'translator' && (
        <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-12">
          <div className="text-center mb-8">
            <span className="text-accent-brown font-bold text-xs uppercase tracking-widest block mb-2">Aplikasi Utama</span>
            <h2 className="font-heading font-bold text-3xl">Penerjemah & Detektor Kesopanan</h2>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">

            {/* Split Screen Translator */}
            <div className="lg:col-span-2 flex flex-col gap-6 bg-white border border-border-color rounded-2xl shadow-md overflow-hidden">
              <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-border-color">

                {/* Source Input Panel */}
                <div className="flex flex-col min-h-[350px]">
                  <div className="bg-bg-cream px-5 py-3.5 border-b border-border-color flex justify-between items-center">
                    <select className="bg-white border border-border-color rounded-md px-3 py-1.5 font-semibold text-sm text-primary outline-none" value={sourceLang} onChange={(e) => setSourceLang(e.target.value)}>
                      <option value="id">Bahasa Indonesia</option>
                      <option value="jv">Bahasa Jawa</option>
                      <option value="mad">Bahasa Madura</option>
                    </select>
                    <button className="text-text-muted hover:text-primary p-1.5 rounded-md hover:bg-neutral-light cursor-pointer" onClick={() => setInputText('')} title="Hapus teks">
                      <X size={16} />
                    </button>
                  </div>
                  <div className="flex-1 p-5 relative">
                    <textarea className="w-full h-full min-h-[220px] border-none outline-none resize-none text-base text-text-dark bg-transparent" placeholder="Ketik kata atau kalimat di sini untuk mendeteksi kesopanan..." value={inputText} onChange={(e) => setInputText(e.target.value)} maxLength={5000} />
                  </div>
                  <div className="bg-neutral-light/35 border-t border-border-color px-5 py-3 flex justify-between items-center">
                    <span className="text-xs text-text-muted font-medium">{inputText.length} / 5000 karakter</span>
                  </div>
                </div>

                {/* Target Output Panel */}
                <div className="flex flex-col min-h-[350px] relative" aria-busy={translationLoading}>

                  {/* Language swap button (Floating in middle for large screens) */}
                  <button className="absolute -left-5 top-3 z-10 w-9 h-9 bg-white border border-border-color rounded-full shadow-md flex items-center justify-center text-accent-brown hover:bg-primary hover:text-white dark:hover:text-neutral-950 cursor-pointer smooth-transition hidden md:flex" onClick={handleSwapLanguages} title="Tukar bahasa">
                    <ArrowLeftRight size={14} />
                  </button>

                  <div className="bg-bg-cream px-5 py-3.5 border-b border-border-color flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <select className="bg-white border border-border-color rounded-md px-3 py-1.5 font-semibold text-sm text-primary outline-none" value={targetLang} onChange={(e) => setTargetLang(e.target.value)}>
                        <option value="id">Bahasa Indonesia</option>
                        <option value="jv">Bahasa Jawa</option>
                        <option value="mad">Bahasa Madura</option>
                      </select>

                      {/* Politeness levels for regional output */}
                      {targetLang !== 'id' && (
                        <div className="flex bg-white border border-border-color p-0.5 rounded-md text-xs font-semibold">
                          <button className={`px-2 py-1 rounded-sm ${targetLevel === 'low' ? 'bg-primary text-white' : 'text-text-medium'}`} onClick={() => setTargetLevel('low')}>
                            {targetLang === 'jv' ? 'Ngoko' : 'Enja-Iya'}
                          </button>
                          <button className={`px-2 py-1 rounded-sm ${targetLevel === 'high' ? 'bg-primary text-white' : 'text-text-medium'}`} onClick={() => setTargetLevel('high')}>
                            {targetLang === 'jv' ? 'Krama' : 'Engghi-Bh'}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex-1 p-5">
                    {translatedText ? (
                      <div className="text-base text-text-dark whitespace-pre-wrap">{translatedText}</div>
                    ) : (
                      <div className="text-text-muted text-base italic">Hasil terjemahan akan muncul di sini...</div>
                    )}
                  </div>
                  <div className="bg-neutral-light/35 border-t border-border-color px-5 py-3 flex justify-between items-center gap-3">
                    <span className="text-[11px] text-text-muted font-medium truncate min-w-0">
                      {translationStatus}
                    </span>
                    <div className="flex gap-2 shrink-0">
                      <button className="text-text-medium hover:text-primary p-1.5 rounded-md hover:bg-neutral-light cursor-pointer" onClick={() => copyToClipboard(translatedText)} title="Salin terjemahan">
                        <Copy size={16} />
                      </button>
                    </div>
                  </div>
                </div>

              </div>
            </div>

            {/* Sidebar Diagnostics */}
            <div className="flex flex-col gap-6">

              {/* Cultural Context */}
              <div className="bg-white border-l-4 border-accent-brown border border-border-color rounded-r-2xl rounded-l-md p-6 shadow-md">
                <h4 className="font-heading font-bold text-sm text-accent-brown mb-2">Panduan Etika Budaya</h4>
                <p className="text-xs text-text-medium leading-relaxed mb-4">{culturalContext}</p>
                {suggestedVersion && (
                  <div className="border-t border-neutral-light pt-3 mt-3">
                    <span className="text-[10px] text-text-muted font-semibold block mb-1">REKOMENDASI VERSI LAIN:</span>
                    <p className="text-xs font-semibold text-primary italic">&quot;{suggestedVersion}&quot;</p>
                  </div>
                )}
              </div>

              <div className="bg-white border border-border-color rounded-2xl p-6 shadow-md">
                <h4 className="font-heading font-bold text-sm text-primary mb-3">Kesopanan</h4>
                <p className="text-xs text-text-medium mb-4">{politenessAnalysis.summary}</p>
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-[11px] font-semibold mb-1">
                      <span className="text-orange-600">Kasual</span>
                      <span>{politenessAnalysis.ngoko}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-neutral-light overflow-hidden">
                      <div className="h-full bg-orange-500 smooth-transition" style={{ width: `${politenessAnalysis.ngoko}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-[11px] font-semibold mb-1">
                      <span className="text-blue-600">Sopan</span>
                      <span>{politenessAnalysis.krama}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-neutral-light overflow-hidden">
                      <div className="h-full bg-blue-500 smooth-transition" style={{ width: `${politenessAnalysis.krama}%` }} />
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </main>
      )}

      {/* DETECTOR PAGE VIEW */}
      {activePage === 'detector' && (
        <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-12">
          <div className="text-center mb-8">
            <span className="text-accent-brown font-bold text-xs uppercase tracking-widest block mb-2">Detektor AI</span>
            <h2 className="font-heading font-bold text-3xl">Deteksi Bahasa & Tingkat Kesopanan</h2>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
            {/* Input Box */}
            <div className="lg:col-span-2 bg-white border border-border-color rounded-2xl shadow-md p-6">
              <h3 className="font-heading font-semibold text-lg text-primary mb-4">Masukkan Teks</h3>
              <textarea
                className="w-full min-h-[200px] p-4 border border-border-color rounded-xl outline-none resize-none text-base text-text-dark bg-transparent focus:border-primary smooth-transition"
                placeholder="Masukkan kata atau kalimat di sini untuk mendeteksi bahasa dan ragam kesopanannya (Indonesia, Jawa, atau Madura)..."
                value={detectorInput}
                onChange={(e) => setDetectorInput(e.target.value)}
              />
              <div className="flex justify-between items-center mt-4">
                <span className="text-xs text-text-medium">{detectorInput.length} karakter</span>
                <button
                  className="bg-primary hover:bg-primary-light text-white font-semibold px-6 py-2.5 rounded-xl shadow-md hover:-translate-y-0.5 smooth-transition cursor-pointer disabled:bg-neutral-medium disabled:cursor-not-allowed"
                  onClick={handleDetectRegister}
                  disabled={!detectorInput.trim() || loadingDetect}
                >
                  {loadingDetect ? 'Menganalisis...' : 'Analisis Teks'}
                </button>
              </div>
            </div>

            {/* Results Panel */}
            <div className="flex flex-col gap-6">
              <div className="bg-white border border-border-color rounded-2xl p-6 shadow-md">
                <h3 className="font-heading font-bold text-lg text-primary flex items-center gap-2 pb-3.5 border-b border-neutral-light mb-5">
                  Hasil Analisis
                </h3>
                {detectorResult ? (
                  <div className="flex flex-col gap-4">
                    <div>
                      <span className="text-xs text-text-muted font-bold block mb-1">BAHASA TERDETEKSI:</span>
                      <span className="bg-primary/10 border border-primary/20 text-primary font-bold text-sm px-3 py-1.5 rounded-lg inline-block">
                        {detectorResult.language}
                      </span>
                    </div>
                    <div>
                      <span className="text-xs text-text-muted font-bold block mb-1">TINGKAT KESOPANAN / REGISTER:</span>
                      <span className="bg-accent-gold/10 border border-accent-gold/20 text-accent-brown font-extrabold text-sm px-3 py-1.5 rounded-lg inline-block uppercase tracking-wide">
                        {detectorResult.register}
                      </span>
                    </div>

                    {/* Persentase Kesopanan */}
                    {(detectorResult.ngokoPercentage !== undefined && detectorResult.kramaPercentage !== undefined) && (
                      <div className="border-t border-neutral-light pt-3">
                        <span className="text-xs text-text-muted font-bold block mb-2">PERSENTASE KESOPANAN:</span>
                        <div className="flex items-center gap-3">
                          <div className="flex-1">
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-orange-600 font-semibold">Kasual (Ngoko)</span>
                              <span className="font-bold">{detectorResult.ngokoPercentage}%</span>
                            </div>
                            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                              <div className="bg-orange-500 h-2.5 rounded-full smooth-transition" style={{ width: `${detectorResult.ngokoPercentage}%` }} />
                            </div>
                          </div>
                          <div className="flex-1">
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-blue-600 font-semibold">Sopan (Krama)</span>
                              <span className="font-bold">{detectorResult.kramaPercentage}%</span>
                            </div>
                            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                              <div className="bg-blue-500 h-2.5 rounded-full smooth-transition" style={{ width: `${detectorResult.kramaPercentage}%` }} />
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Analisis Per-Kata */}
                    {detectorResult.wordAnalysis && detectorResult.wordAnalysis.length > 0 && (
                      <div className="border-t border-neutral-light dark:border-gray-700 pt-3">
                        <span className="text-xs text-text-muted font-bold block mb-3">ANALISIS PER-KATA:</span>
                        <div className="bg-white dark:bg-gray-900 border border-border-color dark:border-gray-700 rounded-xl p-4">
                          <div className="flex flex-wrap gap-2">
                            {detectorResult.wordAnalysis.map((wa, idx) => {
                              const langColor = wa.language === 'Jawa' ? 'bg-green-100 border-green-300 dark:bg-green-900/40 dark:border-green-600'
                                : wa.language === 'Madura' ? 'bg-purple-100 border-purple-300 dark:bg-purple-900/40 dark:border-purple-600'
                                : wa.language === 'Indonesia' ? 'bg-blue-100 border-blue-300 dark:bg-blue-900/40 dark:border-blue-600'
                                : 'bg-gray-100 border-gray-300 dark:bg-gray-700 dark:border-gray-500';
                              const textColor = wa.language === 'Jawa' ? 'text-green-900 dark:text-green-200'
                                : wa.language === 'Madura' ? 'text-purple-900 dark:text-purple-200'
                                : wa.language === 'Indonesia' ? 'text-blue-900 dark:text-blue-200'
                                : 'text-gray-900 dark:text-gray-200';
                              return (
                                <span key={idx} className={`inline-flex flex-col items-center px-3 py-2 rounded-lg border ${langColor}`}>
                                  <span className={`font-bold text-sm ${textColor}`}>{wa.word}</span>
                                  <span className={`text-[10px] font-medium mt-0.5 opacity-75 ${textColor}`}>{wa.language} • {wa.level}</span>
                                </span>
                              );
                            })}
                          </div>
                        </div>
                        <div className="flex gap-4 mt-3 text-[11px] text-text-muted">
                          <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-green-500 rounded-full" /> Jawa</span>
                          <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-purple-500 rounded-full" /> Madura</span>
                          <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-blue-500 rounded-full" /> Indonesia</span>
                          <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-gray-400 rounded-full" /> Asing</span>
                        </div>
                      </div>
                    )}

                    <div className="border-t border-neutral-light pt-3 mt-1">
                      <span className="text-xs text-text-muted font-bold block mb-1">PENJELASAN LINGUISTIK:</span>
                      <p className="text-xs text-text-medium leading-relaxed">{detectorResult.explanation}</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-text-muted italic">Silakan masukkan teks dan klik Analisis Teks untuk melihat hasil.</p>
                )}
              </div>
            </div>
          </div>
        </main>
      )}

      {/* DOCUMENT TRANSLATOR PAGE VIEW */}
      {activePage === 'doc-translator' && (
        <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-12">
          <div className="text-center mb-8">
            <span className="text-accent-brown font-bold text-xs uppercase tracking-widest block mb-2">Pemrosesan Dokumen</span>
            <h2 className="font-heading font-bold text-3xl">Penerjemah Dokumen (PDF, DOCX, DOC, TXT)</h2>
          </div>

          <div className="flex flex-col gap-6">

            {/* Drag & Drop Upload Container */}
            {!uploadedFile ? (
              <div className="bg-white border-2 border-dashed border-accent-brown/30 hover:border-primary hover:bg-primary/2 rounded-2xl p-10 text-center cursor-pointer smooth-transition shadow-sm flex flex-col items-center" onDragOver={handleDragOver} onDrop={handleDrop} onClick={() => fileInputRef.current?.click()}>
                <input type="file" ref={fileInputRef} className="hidden" accept=".pdf,.docx,.doc,.txt" onChange={handleFileSelect} />
                <div className="w-16 h-16 bg-primary-transparent border border-primary/5 rounded-2xl flex items-center justify-center text-accent-brown mb-6 hover:scale-105 smooth-transition">
                  <FileUp size={30} />
                </div>
                <h3 className="font-heading font-semibold text-lg mb-2 text-text-dark">Tarik dan lepas dokumen Anda di sini</h3>
                <p className="text-text-medium text-sm mb-6">Atau klik untuk menelusuri file dari folder Anda</p>
                <span className="text-xs text-text-muted">Mendukung berkas PDF, DOC, DOCX, dan TXT (Ukuran Maks: 10MB)</span>
              </div>
            ) : (
              // File Preview Card
              <div className="bg-white border border-border-color rounded-2xl p-6 shadow-md flex flex-col gap-5">
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-white ${
                    (uploadedFile.name.endsWith('.docx') || uploadedFile.name.endsWith('.doc')) ? 'bg-blue-600' : 
                    uploadedFile.name.endsWith('.pdf') ? 'bg-red-500' : 'bg-emerald-600'
                  }`}>
                    <FileText size={22} />
                  </div>
                  <div>
                    <h4 className="font-heading font-semibold text-sm text-text-dark line-clamp-1">{uploadedFile.name}</h4>
                    <p className="text-xs text-text-muted">{(uploadedFile.size / (1024 * 1024)).toFixed(2)} MB</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_auto_auto] gap-3 md:items-end">
                  <label className="flex flex-col gap-1.5">
                    <span className="text-xs font-semibold text-text-medium">Bahasa sumber</span>
                    <select className="bg-bg-cream border border-border-color rounded-md px-2.5 py-2 font-semibold text-xs text-primary outline-none" value={docSourceLang} onChange={(e) => setDocSourceLang(e.target.value)}>
                      <option value="id">Bahasa Indonesia</option>
                      <option value="jv">Bahasa Jawa</option>
                      <option value="mad">Bahasa Madura</option>
                    </select>
                  </label>
                  <label className="flex flex-col gap-1.5">
                    <span className="text-xs font-semibold text-text-medium">Bahasa target</span>
                    <select className="bg-bg-cream border border-border-color rounded-md px-2.5 py-2 font-semibold text-xs text-primary outline-none" value={docTargetLang} onChange={(e) => setDocTargetLang(e.target.value)}>
                      <option value="jv">Bahasa Jawa</option>
                      <option value="mad">Bahasa Madura</option>
                      <option value="id">Bahasa Indonesia</option>
                    </select>
                  </label>
                  <div className="flex flex-col gap-1.5">
                    <span className="text-xs font-semibold text-text-medium">Ragam target</span>
                    <div className="flex bg-bg-cream border border-border-color p-0.5 rounded-md text-xs font-semibold min-h-9">
                      <button className={`px-3 py-1.5 rounded-sm ${docTargetLevel === 'low' ? 'bg-primary text-white' : 'text-text-medium'} ${docTargetLang === 'id' ? 'opacity-50 cursor-not-allowed' : ''}`} onClick={() => setDocTargetLevel('low')} disabled={docTargetLang === 'id'}>
                        {docTargetLang === 'mad' ? 'Enja-Iya' : 'Ngoko'}
                      </button>
                      <button className={`px-3 py-1.5 rounded-sm ${docTargetLevel === 'high' ? 'bg-primary text-white' : 'text-text-medium'} ${docTargetLang === 'id' ? 'opacity-50 cursor-not-allowed' : ''}`} onClick={() => setDocTargetLevel('high')} disabled={docTargetLang === 'id'}>
                        {docTargetLang === 'mad' ? 'Engghi' : 'Krama'}
                      </button>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button className="bg-primary hover:bg-primary-light text-white font-semibold text-xs px-4 py-2 rounded-lg flex items-center gap-2 cursor-pointer smooth-transition disabled:bg-neutral-medium disabled:cursor-not-allowed" onClick={startDocumentTranslation} disabled={docProgress >= 0 && docProgress < 100}>
                      Mulai <Play size={12} fill="white" />
                    </button>
                    <button className="border border-border-color hover:bg-red-50 hover:border-red-200 text-text-muted hover:text-red-500 p-2 rounded-lg cursor-pointer smooth-transition disabled:opacity-50" onClick={clearDocument} disabled={docProgress >= 0 && docProgress < 100} title="Hapus berkas">
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Translation Progress Bar */}
            {docProgress >= 0 && docProgress < 100 && (
              <div className="bg-white border border-border-color rounded-xl p-5 shadow-sm">
                <div className="flex justify-between text-xs font-semibold mb-2">
                  <span className="text-primary">{docProgressStep}</span>
                  <span>{docProgress}%</span>
                </div>
                <div className="w-full h-2 bg-neutral-light rounded-full overflow-hidden">
                  <div className="h-full bg-linear-to-r from-primary to-accent-gold" style={{ width: `${docProgress}%` }} />
                </div>
              </div>
            )}

            {docError && (
              <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm flex items-start gap-3">
                <AlertCircle size={18} className="shrink-0 mt-0.5" />
                <span>{docError}</span>
              </div>
            )}

            {/* Document Download & Summary */}
            {docProgress === 100 && docTranslatedName && (
              <div className="bg-primary/5 border border-primary/20 rounded-2xl p-6 shadow-sm flex flex-col gap-5 animation-fadeIn">
                <div className="flex flex-col md:flex-row justify-between md:items-center gap-4">
                  <div>
                    <h4 className="font-heading font-semibold text-primary mb-1">Penerjemahan Selesai</h4>
                    <p className="text-xs text-text-medium mb-1 font-semibold">{docTranslatedName}</p>
                    <span className="text-[10px] text-text-muted">
                      {docWordsTranslated} kata diproses - {docPolitenessSummary || 'Netral'}
                    </span>
                  </div>
                  <button
                    className="bg-accent-brown hover:bg-accent-brown-light text-white font-semibold text-sm px-5 py-2.5 rounded-xl flex items-center justify-center gap-2 cursor-pointer shadow-md smooth-transition disabled:opacity-60 disabled:cursor-not-allowed"
                    onClick={downloadTranslatedDocument}
                    disabled={!docDownloadUrl || docDownloading}
                  >
                    {docDownloading ? 'Menyiapkan...' : 'Unduh Berkas'} <Download size={14} />
                  </button>
                </div>

                <div className="bg-white border border-border-color rounded-xl p-4">
                  <div className="flex justify-between items-center gap-3 mb-3">
                    <h5 className="font-heading font-semibold text-sm text-primary">Teks Terjemahan</h5>
                    <button className="text-text-medium hover:text-primary p-1.5 rounded-md hover:bg-neutral-light cursor-pointer" onClick={() => copyToClipboard(docTranslatedText)} title="Salin hasil terjemahan">
                      <Copy size={15} />
                    </button>
                  </div>
                  <div className="max-h-[320px] overflow-auto whitespace-pre-wrap text-sm text-text-dark leading-relaxed">
                    {docTranslatedText || 'Tidak ada teks yang berhasil diekstrak dari dokumen.'}
                  </div>
                  {docPreviewTruncated && (
                    <p className="text-[11px] text-text-muted mt-3">
                      Pratinjau dipotong karena dokumen panjang. Berkas unduhan berisi hasil lengkap.
                    </p>
                  )}
                </div>
              </div>
            )}

          </div>
        </main>
      )}

      {/* LANGUAGE INSIGHTS VIEW */}
      {activePage === 'insights' && (
        <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-12">
          <div className="text-center mb-8">
            <span className="text-accent-brown font-bold text-xs uppercase tracking-widest block mb-2">Portal Data Preservasi</span>
            <h2 className="font-heading font-bold text-3xl">Analitik Bahasa</h2>
          </div>

          {/* Metrics row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-white border border-border-color rounded-2xl p-5 shadow-xs flex items-center gap-4">
              <div className="w-11 h-11 bg-primary-transparent border border-primary/5 rounded-full flex items-center justify-center text-primary">
                <BookOpen size={18} />
              </div>
              <div>
                <h5 className="text-[10px] text-text-muted uppercase tracking-wider font-bold mb-0.5">Kosakata Terjaga</h5>
                <p className="font-heading font-bold text-xl text-text-dark">
                  {insightsData ? formatMetric(insightsData.metrics.total_vocabulary) : insightsLoading ? '...' : '0'}
                </p>
              </div>
            </div>

            <div className="bg-white border border-border-color rounded-2xl p-5 shadow-xs flex items-center gap-4">
              <div className="w-11 h-11 bg-accent-gold-glow/45 border border-accent-gold/5 rounded-full flex items-center justify-center text-accent-brown">
                <Users size={18} />
              </div>
              <div>
                <h5 className="text-[10px] text-text-muted uppercase tracking-wider font-bold mb-0.5">Terjemahan Tercatat</h5>
                <p className="font-heading font-bold text-xl text-text-dark">
                  {insightsData ? formatMetric(insightsData.metrics.total_translations) : insightsLoading ? '...' : '0'}
                </p>
              </div>
            </div>

            <div className="bg-white border border-border-color rounded-2xl p-5 shadow-xs flex items-center gap-4">
              <div className="w-11 h-11 bg-primary-transparent border border-primary/5 rounded-full flex items-center justify-center text-primary">
                <Globe size={18} />
              </div>
              <div>
                <h5 className="text-[10px] text-text-muted uppercase tracking-wider font-bold mb-0.5">Status Data</h5>
                <p className="font-heading font-bold text-xl text-primary">
                  {insightsData ? insightsData.metrics.vitality_status : insightsLoading ? '...' : 'Belum ada'}
                </p>
              </div>
            </div>

            <div className="bg-white border border-border-color rounded-2xl p-5 shadow-xs flex items-center gap-4">
              <div className="w-11 h-11 bg-accent-gold-glow/45 border border-accent-gold/5 rounded-full flex items-center justify-center text-accent-brown">
                <Activity size={18} />
              </div>
              <div>
                <h5 className="text-[10px] text-text-muted uppercase tracking-wider font-bold mb-0.5">Kemunculan Resmi</h5>
                <p className="font-heading font-bold text-xl text-text-dark">
                  {insightsData ? formatMetric(insightsData.metrics.total_vocab_usage || 0) : insightsLoading ? '...' : '0'}
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">

            {/* Word of the Day (Left Box) */}
              <div className="bg-gradient-to-br from-primary to-primary-light dark:from-[#111614] dark:to-[#080A09] dark:border dark:border-border-color text-white dark:text-text-dark rounded-3xl p-6 shadow-md flex flex-col justify-between min-h-[300px]">
              <div>
                <span className="text-[10px] text-accent-gold tracking-widest font-extrabold uppercase block mb-1">Kata Daerah Hari Ini</span>
                <div className="font-heading font-bold text-4xl text-white dark:text-[#65B29A] mb-2">{WOTD_WORDS[wotdIndex].word}</div>
                <div className="flex items-center gap-2 mb-6">
                  <span className="text-xs text-[#FFDF7B] dark:text-accent-gold italic font-semibold">{WOTD_WORDS[wotdIndex].spell} ({WOTD_WORDS[wotdIndex].type})</span>
                </div>
              </div>
              <div className="border-t border-white/10 dark:border-border-color pt-4">
                <span className="text-[10px] text-neutral-200 dark:text-text-muted font-bold block uppercase mb-1">Arti (Bahasa Indonesia):</span>
                <p className="text-sm leading-relaxed mb-3 text-white dark:text-text-medium font-medium">{WOTD_WORDS[wotdIndex].mean}</p>
                <span className="text-[10px] text-neutral-200 dark:text-text-muted font-bold block uppercase mb-1">Contoh Kalimat:</span>
                <p className="text-xs italic text-white dark:text-text-medium">{WOTD_WORDS[wotdIndex].ex}</p>
              </div>
            </div>

            {/* Popular Vocabulary (Right Box) */}
            <div className="bg-white border border-border-color rounded-3xl p-6 shadow-md flex flex-col justify-between">
              <h3 className="font-heading font-bold text-lg text-primary mb-4">Kosakata Terpopuler</h3>
              <div className="flex flex-col gap-3">
                {insightsLoading && !insightsData ? (
                  <div className="bg-bg-cream border border-border-color px-4 py-4 rounded-lg text-sm text-text-muted">
                    Memuat kosakata resmi dari aktivitas terjemahan...
                  </div>
                ) : insightsData && insightsData.popular_words.length > 0 ? (
                  insightsData.popular_words.map((item) => (
                    <div key={`${item.language}-${item.word}`} className="flex justify-between items-center gap-4 bg-bg-cream border border-border-color px-4 py-2.5 rounded-lg">
                      <div className="min-w-0">
                        <h4 className="font-heading font-semibold text-sm capitalize truncate">{item.word}</h4>
                        <p className="text-[11px] text-text-muted truncate">
                          {(item.languageName || item.language).replace('Bahasa ', '')} &rarr; {item.meaning || 'kosakata resmi'}
                        </p>
                      </div>
                      <div className="text-right shrink-0">
                        <div className="text-xs font-bold text-primary">{formatSearchCount(item.count)}</div>
                        <span className="text-[9px] font-semibold text-accent-brown">{item.register || 'Terverifikasi'}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="bg-bg-cream border border-border-color px-4 py-4 rounded-lg text-sm text-text-muted">
                    Belum ada kosakata resmi yang tercatat dari terjemahan pengguna.
                  </div>
                )}
              </div>
            </div>

          </div>

          {/* SVG Custom Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            {/* SVG Line Chart: Vitality Trends */}
            <div className="bg-white border border-border-color rounded-3xl p-6 shadow-md">
              <h3 className="font-heading font-bold text-base text-primary mb-1">Penurunan Penggunaan Bahasa Ibu per Generasi</h3>
              <p className="text-xs text-text-muted mb-6">Persentase Pemuda Fasih Bahasa Daerah (1960 - 2026)</p>

              <div className="relative w-full h-[200px]">
                <svg className="w-full h-full" viewBox="0 0 500 200">
                  {/* Grid Lines */}
                  <line x1="40" y1="20" x2="480" y2="20" stroke="#F1F3F4" strokeWidth="1" />
                  <line x1="40" y1="60" x2="480" y2="60" stroke="#F1F3F4" strokeWidth="1" />
                  <line x1="40" y1="100" x2="480" y2="100" stroke="#F1F3F4" strokeWidth="1" />
                  <line x1="40" y1="140" x2="480" y2="140" stroke="#F1F3F4" strokeWidth="1" />
                  <line x1="40" y1="180" x2="480" y2="180" stroke="#E6ECE8" strokeWidth="1.5" />

                  {/* Y Axis Labels */}
                  <text x="10" y="24" fill="#7D8F86" fontSize="10">100%</text>
                  <text x="15" y="104" fill="#7D8F86" fontSize="10">50%</text>
                  <text x="20" y="184" fill="#7D8F86" fontSize="10">0%</text>

                  {/* X Axis Labels */}
                  <text x="40" y="196" fill="#7D8F86" fontSize="9" textAnchor="middle">1960</text>
                  <text x="150" y="196" fill="#7D8F86" fontSize="9" textAnchor="middle">1980</text>
                  <text x="260" y="196" fill="#7D8F86" fontSize="9" textAnchor="middle">2000</text>
                  <text x="370" y="196" fill="#7D8F86" fontSize="9" textAnchor="middle">2020</text>
                  <text x="470" y="196" fill="#7D8F86" fontSize="9" textAnchor="middle">2026</text>

                  {/* Javanese Line Path */}
                  <path d="M 40 25 L 150 40 L 260 70 L 370 100 L 470 115" fill="none" stroke="var(--color-primary)" strokeWidth="3" />
                  {/* Javanese Data points */}
                  <circle cx="40" cy="25" r="4" fill="var(--color-primary)" />
                  <circle cx="150" cy="40" r="4" fill="var(--color-primary)" />
                  <circle cx="260" cy="70" r="4" fill="var(--color-primary)" />
                  <circle cx="370" cy="100" r="4" fill="var(--color-primary)" />
                  <circle cx="470" cy="115" r="4" fill="var(--color-primary)" />

                  {/* Madurese Line Path */}
                  <path d="M 40 30 L 150 50 L 260 80 L 370 115 L 470 130" fill="none" stroke="var(--color-accent-brown)" strokeWidth="3" />
                  {/* Madurese Data points */}
                  <circle cx="40" cy="30" r="4" fill="var(--color-accent-brown)" />
                  <circle cx="150" cy="50" r="4" fill="var(--color-accent-brown)" />
                  <circle cx="260" cy="80" r="4" fill="var(--color-accent-brown)" />
                  <circle cx="370" cy="115" r="4" fill="var(--color-accent-brown)" />
                  <circle cx="470" cy="130" r="4" fill="var(--color-accent-brown)" />
                </svg>
              </div>
              <div className="flex gap-6 justify-center mt-3 text-xs font-semibold">
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-1.5 bg-primary rounded-xs" />
                  <span>Bahasa Jawa</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-1.5 bg-accent-brown rounded-xs" />
                  <span>Bahasa Madura</span>
                </div>
              </div>
            </div>

            {/* SVG Pie Chart: Request distribution */}
            <div className="bg-white border border-border-color rounded-3xl p-6 shadow-md">
              <h3 className="font-heading font-bold text-base text-primary mb-1">Distribusi Kategori Terjemahan</h3>
              <p className="text-xs text-text-muted mb-6">Persentase Tingkat Tutur yang Dicari Pengguna</p>

              <div className="flex flex-col sm:flex-row items-center gap-8 justify-center h-[200px]">
                {/* SVG Doughnut */}
                <svg width="150" height="150" viewBox="0 0 36 36">
                  <circle cx="18" cy="18" r="15.915" fill="none" stroke="#F1F3F4" strokeWidth="4" />

                  {/* Jawa Ngoko (42%) */}
                  <circle cx="18" cy="18" r="15.915" fill="none" stroke="var(--color-primary)" strokeWidth="4" strokeDasharray="42 58" strokeDashoffset="25" />

                  {/* Jawa Krama (38%) */}
                  <circle cx="18" cy="18" r="15.915" fill="none" stroke="var(--color-accent-gold)" strokeWidth="4" strokeDasharray="38 62" strokeDashoffset="83" />

                  {/* Madura Enja-Iya (12%) */}
                  <circle cx="18" cy="18" r="15.915" fill="none" stroke="var(--color-accent-brown)" strokeWidth="4" strokeDasharray="12 88" strokeDashoffset="45" />

                  {/* Madura Engghi-Bhanten (8%) */}
                  <circle cx="18" cy="18" r="15.915" fill="none" stroke="var(--color-primary-light)" strokeWidth="4" strokeDasharray="8 92" strokeDashoffset="33" />
                </svg>

                <div className="grid grid-cols-2 sm:grid-cols-1 gap-3 text-xs font-semibold">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-primary rounded-xs" />
                    <span>Jawa Ngoko (42%)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-accent-gold rounded-xs" />
                    <span>Jawa Krama (38%)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-accent-brown rounded-xs" />
                    <span>Madura Enja-Iya (12%)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-primary-light rounded-xs" />
                    <span>Madura Engghi-B (8%)</span>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </main>
      )}

      {/* ABOUT PAGE VIEW */}
      {activePage === 'about' && (
        <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-12">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h1 className="font-heading font-extrabold text-3xl md:text-4xl text-primary mb-3">Tentang Lokalator</h1>
            <p className="text-text-medium text-sm md:text-base leading-relaxed">Melestarikan kekayaan budaya bahasa daerah di Indonesia melalui keunggulan kecerdasan buatan.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">

            {/* Vision & Mission */}
            <div className="bg-white border border-border-color rounded-3xl p-6 md:p-8 shadow-md">
              <h3 className="font-heading font-bold text-xl text-primary mb-4 pb-2 border-b border-accent-gold-glow">Visi & Misi</h3>
              <p className="text-text-medium text-sm leading-relaxed mb-4">
                Bahasa daerah merupakan aset warisan budaya nasional yang tiada tara. Namun, seiring berjalannya waktu, kefasihan penggunaan tingkat tutur yang baik seperti *Undha-Usuk* pada bahasa Jawa dan tata tutur bahasa Madura kian merosot di kalangan pemuda.
              </p>
              <p className="text-text-medium text-sm leading-relaxed mb-6 font-semibold text-primary">
                Lokalator bertekad menjadi solusi digital terdepan untuk menjembatani preservasi aksara daerah melalui teknologi terapan.
              </p>

              <ul className="flex flex-col gap-3 list-none">
                <li className="flex gap-2.5 text-xs text-text-medium">
                  <CheckCircle2 size={16} className="text-primary shrink-0" />
                  <span>Membangun mesin penerjemah bahasa daerah dengan pemahaman konteks kesopanan sosial (unggah-ungguh).</span>
                </li>
                <li className="flex gap-2.5 text-xs text-text-medium">
                  <CheckCircle2 size={16} className="text-primary shrink-0" />
                  <span>Mengintegrasikan ekstraksi file dokumen berekstensi PDF, DOCX, DOC, dan TXT untuk kebutuhan administrasi publik daerah.</span>
                </li>
                <li className="flex gap-2.5 text-xs text-text-medium">
                  <CheckCircle2 size={16} className="text-primary shrink-0" />
                  <span>Menyediakan instrumen statistik dan data terbuka preservasi linguistik untuk kebutuhan riset akademisi.</span>
                </li>
              </ul>
            </div>

            {/* University Project Information */}
            <div className="bg-white border border-border-color rounded-3xl p-6 md:p-8 shadow-md">
              <h3 className="font-heading font-bold text-xl text-primary mb-4 pb-2 border-b border-accent-gold-glow">Informasi Capstone</h3>
              <p className="text-text-medium text-sm leading-relaxed mb-4">
                Lokalator dirancang sebagai Final Project mata kuliah Kecerdasan Artifisial dan Machine Learning Kelompok 7 Kelas A.
              </p>

              <div className="border border-border-color rounded-xl overflow-hidden mb-6">
                <table className="w-full text-xs text-left border-collapse">
                  <tbody>
                    <tr className="border-b border-border-color">
                      <td className="px-4 py-3 bg-bg-cream text-primary font-bold w-1/3">Mata Kuliah</td>
                      <td className="px-4 py-3 text-text-medium">Kecerdasan Artifisial dan Machine Learning</td>
                    </tr>
                    <tr className="border-b border-border-color">
                      <td className="px-4 py-3 bg-bg-cream text-primary font-bold">Kelompok</td>
                      <td className="px-4 py-3 text-text-medium">Kelompok 7 - Kelas A</td>
                    </tr>
                    <tr className="border-b border-border-color">
                      <td className="px-4 py-3 bg-bg-cream text-primary font-bold">Integrasi Stack</td>
                      <td className="px-4 py-3 text-text-medium">Next.js 14, FastAPI Backend, SQLite, PyMuPDF</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 bg-bg-cream text-primary font-bold">Model Klasifikasi</td>
                      <td className="px-4 py-3 text-text-medium">MarianMT, IndoBERT Classifier, Random Forest</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div>
                <h4 className="font-heading font-bold text-sm text-primary mb-3">Daftar Anggota (Kelompok 7):</h4>
                <div className="grid grid-cols-2 gap-2.5 text-xs text-text-medium">
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 bg-accent-gold rounded-full" />
                    <span>Ahmad Wildan Fawwaz (5027241001)</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 bg-accent-gold rounded-full" />
                    <span>Muhammad Rakha Hananditya Rauf (5027241015)</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 bg-accent-gold rounded-full" />
                    <span>Yasykur Khalis Jati Maulana Yuwono (5027241122)</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 bg-accent-gold rounded-full" />
                    <span>Aras Rizky Ananta (5027221053)</span>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </main>
      )}

      {/* PRIVACY POLICY VIEW */}
      {activePage === 'privacy' && (
        <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-12">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <span className="text-accent-brown font-bold text-xs uppercase tracking-widest block mb-2">Dokumen Legal</span>
            <h1 className="font-heading font-extrabold text-3xl md:text-4xl text-primary mb-3">Kebijakan Privasi</h1>
            <p className="text-text-medium text-sm md:text-base leading-relaxed">Template kebijakan privasi Lokalator. Konten detail dapat diisi sebelum publikasi resmi.</p>
          </div>

          <div className="bg-white border border-border-color rounded-2xl p-6 md:p-8 shadow-md space-y-6">
            <section>
              <h2 className="font-heading font-bold text-lg text-primary mb-2">1. Data yang Dikumpulkan</h2>
              <p className="text-sm text-text-medium leading-relaxed">Tuliskan jenis data yang diproses, misalnya teks terjemahan, metadata penggunaan, dan data unggahan dokumen.</p>
            </section>
            <section>
              <h2 className="font-heading font-bold text-lg text-primary mb-2">2. Penggunaan Data</h2>
              <p className="text-sm text-text-medium leading-relaxed">Jelaskan bagaimana data digunakan untuk menjalankan fitur penerjemahan, deteksi kesopanan, analitik, dan peningkatan kualitas layanan.</p>
            </section>
            <section>
              <h2 className="font-heading font-bold text-lg text-primary mb-2">3. Penyimpanan dan Keamanan</h2>
              <p className="text-sm text-text-medium leading-relaxed">Isi kebijakan retensi, penghapusan dokumen sementara, dan langkah keamanan yang diterapkan.</p>
            </section>
            <section>
              <h2 className="font-heading font-bold text-lg text-primary mb-2">4. Kontak</h2>
              <p className="text-sm text-text-medium leading-relaxed">Tambahkan kontak resmi pengelola Lokalator untuk permintaan privasi atau penghapusan data.</p>
            </section>
          </div>
        </main>
      )}

      {/* TERMS VIEW */}
      {activePage === 'terms' && (
        <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-12">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <span className="text-accent-brown font-bold text-xs uppercase tracking-widest block mb-2">Dokumen Legal</span>
            <h1 className="font-heading font-extrabold text-3xl md:text-4xl text-primary mb-3">Syarat Ketentuan</h1>
            <p className="text-text-medium text-sm md:text-base leading-relaxed">Template syarat ketentuan penggunaan Lokalator. Konten detail dapat diisi sebelum publikasi resmi.</p>
          </div>

          <div className="bg-white border border-border-color rounded-2xl p-6 md:p-8 shadow-md space-y-6">
            <section>
              <h2 className="font-heading font-bold text-lg text-primary mb-2">1. Ketentuan Penggunaan</h2>
              <p className="text-sm text-text-medium leading-relaxed">Tuliskan aturan dasar penggunaan fitur penerjemah, detektor kesopanan, chatbot, dan pemrosesan dokumen.</p>
            </section>
            <section>
              <h2 className="font-heading font-bold text-lg text-primary mb-2">2. Batasan Layanan</h2>
              <p className="text-sm text-text-medium leading-relaxed">Jelaskan bahwa hasil AI dan kamus lokal bersifat bantuan, dapat memiliki keterbatasan, dan perlu verifikasi untuk konteks resmi.</p>
            </section>
            <section>
              <h2 className="font-heading font-bold text-lg text-primary mb-2">3. Hak Kekayaan Intelektual</h2>
              <p className="text-sm text-text-medium leading-relaxed">Isi ketentuan kepemilikan merek, aset, dataset, kode, dan konten yang dihasilkan atau diunggah pengguna.</p>
            </section>
            <section>
              <h2 className="font-heading font-bold text-lg text-primary mb-2">4. Perubahan Ketentuan</h2>
              <p className="text-sm text-text-medium leading-relaxed">Tambahkan mekanisme pembaruan syarat ketentuan dan tanggal berlaku dokumen.</p>
            </section>
          </div>
        </main>
      )}

      {/* Footer */}
      <footer className="bg-primary text-white/80 pt-16 pb-8 border-t-4 border-accent-gold mt-auto px-6 relative">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-10 mb-12">

          <div className="md:col-span-2">
            <div className="flex items-center gap-3 text-white font-heading font-bold text-xl mb-4 cursor-pointer" onClick={() => handleNavigate('landing')}>
              <div className="h-12 w-12 rounded-md bg-white flex items-center justify-center overflow-hidden">
                <Image
                  src="/assets/lokalator_logo_centered.png"
                  alt="Logo Lokalator"
                  width={48}
                  height={48}
                  className="brand-logo h-full w-full scale-90 object-contain"
                />
              </div>
              <span>Lokalator</span>
            </div>
            <p className="text-xs text-white/70 leading-relaxed max-w-sm mb-4">
              Menjaga warisan budaya tutur kata luhur nusantara. Platform penerjemah dan penganalisis tingkat kesopanan bahasa Jawa & Madura presisi berbasis NLP AI.
            </p>
          </div>

          <div>
            <h4 className="text-white font-heading font-bold text-sm mb-4 relative after:content-[''] after:absolute after:-bottom-1.5 after:left-0 after:w-6 after:h-[2px] after:bg-accent-gold">
              Navigasi
            </h4>
            <ul className="flex flex-col gap-2.5 text-xs text-white/75 list-none p-0 mt-3">
              <li className="hover:text-accent-gold cursor-pointer transition-colors" onClick={() => handleNavigate('landing')}>Beranda</li>
              <li className="hover:text-accent-gold cursor-pointer transition-colors" onClick={() => handleNavigate('translator')}>Penerjemah</li>
              <li className="hover:text-accent-gold cursor-pointer transition-colors" onClick={() => handleNavigate('doc-translator')}>Terjemah Dokumen</li>
              <li className="hover:text-accent-gold cursor-pointer transition-colors" onClick={() => handleNavigate('detector')}>Deteksi Kesopanan</li>
              <li className="hover:text-accent-gold cursor-pointer transition-colors" onClick={() => handleNavigate('insights')}>Analitik Bahasa</li>
              <li className="hover:text-accent-gold cursor-pointer transition-colors" onClick={() => handleNavigate('about')}>Tentang</li>
            </ul>
          </div>

          <div>
            <h4 className="text-white font-heading font-bold text-sm mb-4 relative after:content-[''] after:absolute after:-bottom-1.5 after:left-0 after:w-6 after:h-[2px] after:bg-accent-gold">
              Bahasa Daerah
            </h4>
            <ul className="flex flex-col gap-2.5 text-xs text-white/75 list-none p-0 mt-3">
              <li className="hover:text-accent-gold cursor-pointer transition-colors" onClick={() => handleNavigate('translator')}>Jawa Ngoko</li>
              <li className="hover:text-accent-gold cursor-pointer transition-colors" onClick={() => handleNavigate('translator')}>Jawa Krama</li>
              <li className="hover:text-accent-gold cursor-pointer transition-colors" onClick={() => handleNavigate('translator')}>Madura Enja-Iya</li>
              <li className="hover:text-accent-gold cursor-pointer transition-colors" onClick={() => handleNavigate('translator')}>Madura Engghi-Bhanten</li>
            </ul>
          </div>

        </div>

        <div className="max-w-6xl mx-auto pt-8 border-t border-white/10 flex flex-col md:flex-row justify-between items-center text-xs text-white/60 gap-4 text-center">
          <div>&copy; 2026 Lokalator. Final Project Kecerdasan Artifisial dan Machine Learning Kelompok 7.</div>
          <div className="flex gap-4">
            <button type="button" onClick={() => handleNavigate('privacy')} className="hover:text-accent-gold transition-colors cursor-pointer">Kebijakan Privasi</button>
            <button type="button" onClick={() => handleNavigate('terms')} className="hover:text-accent-gold transition-colors cursor-pointer">Syarat Ketentuan</button>
          </div>
        </div>
      </footer>

      {/* Floating Chatbot Widget */}
      {!chatWidgetOpen && (
        <button
          type="button"
          onClick={() => setChatWidgetOpen(true)}
          className="fixed bottom-5 right-5 z-50 h-16 w-16 rounded-full bg-primary text-white shadow-premium border border-white/20 flex items-center justify-center hover:bg-primary-light hover:-translate-y-0.5 smooth-transition cursor-pointer dark:border-white/15 dark:shadow-[0_20px_45px_rgba(0,0,0,0.55)]"
          title="Buka Chatbot AI"
          aria-label="Buka Chatbot AI"
        >
          <MessageCircle size={26} />
        </button>
      )}

      {chatWidgetOpen && (
        <div
          className={`fixed z-50 bottom-2 md:bottom-3 h-[calc(100vh-1rem)] md:h-[calc(100vh-1.5rem)] bg-card-bg border border-border-color rounded-2xl shadow-premium flex flex-col overflow-hidden ${
            chatExpanded
              ? 'left-4 right-4 md:left-1/2 md:right-auto md:w-[min(920px,calc(100vw-3rem))] md:-translate-x-1/2'
              : 'left-4 right-4 md:left-auto md:right-6 md:w-[420px]'
          }`}
        >
          <div className="bg-primary text-white px-4 py-3 flex items-center justify-between gap-3 dark:bg-[#0B0F0D] dark:border-b dark:border-border-color">
            <div className="flex items-center gap-3 min-w-0">
              <div className="h-9 w-9 rounded-lg bg-white flex items-center justify-center overflow-hidden shrink-0">
                <Image
                  src="/assets/lokalator_logo_centered.png"
                  alt="Logo Lokalator"
                  width={36}
                  height={36}
                  className="brand-logo h-full w-full scale-90 object-contain"
                />
              </div>
              <div className="min-w-0">
                <div className="font-heading font-bold text-sm leading-tight">Lokalator AI</div>
                <div className="text-[11px] text-white/75 truncate">Chatbot bahasa Jawa, Madura, dan Indonesia</div>
              </div>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <button
                type="button"
                onClick={() => setChatExpanded((value) => !value)}
                className="p-2 rounded-lg hover:bg-white/10 smooth-transition cursor-pointer"
                title={chatExpanded ? 'Perkecil chatbot' : 'Perbesar chatbot'}
                aria-label={chatExpanded ? 'Perkecil chatbot' : 'Perbesar chatbot'}
              >
                {chatExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
              </button>
              <button
                type="button"
                onClick={() => {
                  setChatWidgetOpen(false);
                  setChatExpanded(false);
                }}
                className="p-2 rounded-lg hover:bg-white/10 smooth-transition cursor-pointer"
                title="Tutup chatbot"
                aria-label="Tutup chatbot"
              >
                <X size={17} />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
            {chatMessages.length === 0 && (
              <div className="text-center text-text-muted py-8">
                <Image
                  src="/assets/lokalator_logo_centered.png"
                  alt="Logo Lokalator"
                  width={112}
                  height={112}
                  className="brand-logo mx-auto mb-4 h-28 w-28 object-contain opacity-100"
                />
                <p className="text-sm">Mulai percakapan dengan mengetik pesan di bawah.</p>
                <div className="mt-4 flex flex-wrap gap-2 justify-center">
                  {['Ajari aku bahasa Jawa!', 'Piye kabare?', 'Apa itu Krama Alus?', 'Sengko\' terro belajar Madura'].map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      onClick={() => setChatInput(suggestion)}
                      className="text-xs bg-primary/5 border border-primary/10 text-primary px-3 py-1.5 rounded-full hover:bg-primary/10 cursor-pointer smooth-transition"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {chatMessages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === 'user'
                    ? 'bg-primary text-white rounded-br-md'
                    : 'bg-neutral-light text-text-dark rounded-bl-md border border-border-color'
                }`}>
                  {msg.text}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex justify-start">
                <div className="bg-neutral-light border border-border-color px-4 py-3 rounded-2xl rounded-bl-md text-sm text-text-muted">
                  <span className="animate-pulse">Mengetik...</span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="border-t border-border-color p-4">
            <div className="flex gap-3">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendChat(); } }}
                placeholder="Ketik pesan..."
                className="flex-1 min-w-0 bg-white border border-border-color rounded-xl px-4 py-3 text-sm text-text-dark placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary smooth-transition"
              />
              <button
                type="button"
                onClick={handleSendChat}
                disabled={chatLoading || !chatInput.trim()}
                className="bg-primary hover:bg-primary-light disabled:bg-gray-300 text-white px-4 py-3 rounded-xl flex items-center gap-2 font-semibold text-sm cursor-pointer smooth-transition disabled:cursor-not-allowed"
                aria-label="Kirim pesan"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Toast Notification */}
      {toastMsg && (
        <div className="fixed top-6 left-1/2 -translate-x-1/2 bg-primary text-white px-5 py-3 rounded-lg shadow-lg flex items-center gap-3 z-50 text-xs font-semibold border border-primary/20 animation-fadeIn smooth-transition">
          <Info size={16} className="text-accent-gold" />
          <span>{toastMsg.text}</span>
        </div>
      )}

    </div>
  );
}
