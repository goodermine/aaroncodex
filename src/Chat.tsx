import { useState, useRef, useEffect } from 'react';
import { trpc } from '@/lib/trpc';
import { useAuth } from '@/_core/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Upload, 
  Send, 
  Loader2, 
  FileAudio,
  Download,
  Bot,
  User,
  CheckCircle2,
  Circle,
  Music2,
  Mic,
  MicOff,
  X
} from 'lucide-react';
import { toast } from 'sonner';
import VoxAINavigation from '@/components/VoxAINavigation';
import { WaveformVisualizer } from '@/components/WaveformVisualizer';
import { AudioWaveformPlayer } from '@/components/AudioWaveformPlayer';
import { StudioMonitor } from '@/components/StudioMonitor';
import { Streamdown } from 'streamdown';
import { getLoginUrl } from '@/const';

interface QuickReply {
  label: string;
  value: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  audioFile?: {
    name: string;
    url: string;
  };
  waveformData?: number[];
  audioMetrics?: {
    avgRms: number;
    peakRms: number;
    dynamicRange: string;
    duration: number;
  };
  quickReplies?: QuickReply[];
}

interface AnalysisStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'completed';
  detail?: string;
}

type ChatState = 
  | 'idle'           // Waiting for file upload
  | 'file_uploaded'  // File uploaded, asking for song name
  | 'awaiting_context' // Asked for context, waiting for response
  | 'analyzing'      // Running analysis
  | 'complete';      // Analysis complete

export default function Chat() {
  const { isAuthenticated, loading: authLoading, user } = useAuth();
  
  // Check if user is invited to VOX AI
  const inviteCheck = trpc.auth.checkInvite.useQuery(undefined, {
    enabled: isAuthenticated,
    retry: false,
  });
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [chatState, setChatState] = useState<ChatState>('idle');
  const [isUploading, setIsUploading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  
  // Analysis state
  const [uploadedFile, setUploadedFile] = useState<{ url: string; name: string; analysisId?: number } | null>(null);
  const [songName, setSongName] = useState('');
  const [userContext, setUserContext] = useState('');
  const [analysisSteps, setAnalysisSteps] = useState<AnalysisStep[]>([]);
  const [finalAnalysis, setFinalAnalysis] = useState<string | null>(null);
  const [analysisId, setAnalysisId] = useState<number | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Voice input state
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  // tRPC mutations
  const uploadMutation = trpc.analysis.upload.useMutation();
  const howardChatMutation = trpc.analysis.howardChat.useMutation();
  const phraseBreakdownMutation = trpc.analysis.phraseBreakdown.useMutation();

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, analysisSteps]);

  // Initial welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        id: 'welcome',
        role: 'assistant',
        content: `**Welcome to VOX AI!** 🎤

I'm Howard, your elite vocal coach. I'm excited to hear what you've been working on!

Every voice is unique, and I'm here to help you discover yours. Upload a recording and I'll give you professional feedback using the **VOXAI 6-Phase Protocol**.

My goal is to give you **actionable feedback** so you can learn, do the exercises, come back, upload the new take—even small sections of songs—and help you improve fast.

**Supported:** WAV, MP3, M4A, AAC (up to 100MB)

Tap the upload button to get started!`,
        timestamp: new Date(),
      }]);
    }
  }, []);

  // Handle file upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const validTypes = ['audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/m4a', 'audio/x-m4a', 'audio/aac', 'audio/mp4'];
    const validExtensions = ['.wav', '.mp3', '.m4a', '.aac'];
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    
    if (!validTypes.includes(file.type) && !validExtensions.includes(fileExtension)) {
      toast.error('Please upload a WAV, MP3, M4A, or AAC file');
      return;
    }

    // Validate file size (100MB)
    if (file.size > 100 * 1024 * 1024) {
      toast.error('File size must be under 100MB');
      return;
    }

    setIsUploading(true);

    try {
      // Convert to base64
      const reader = new FileReader();
      reader.onload = async () => {
        const base64 = (reader.result as string).split(',')[1];
        
        // Upload to server
        const result = await uploadMutation.mutateAsync({
          fileName: file.name,
          fileFormat: fileExtension.replace('.', ''),
          fileSizeBytes: file.size,
          fileBase64: base64,
        });

        setUploadedFile({
          url: result.audioUrl,
          name: file.name,
          analysisId: result.analysisId,
        });

        // Extract waveform data for visualization
        let waveformData: number[] = [];
        let audioMetrics = { avgRms: 0, peakRms: 0, dynamicRange: 'moderate', duration: 0 };
        
        try {
          const audioResponse = await fetch(result.audioUrl);
          const arrayBuffer = await audioResponse.arrayBuffer();
          const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
          const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
          
          // Extract waveform
          const rawData = audioBuffer.getChannelData(0);
          const samples = 150;
          const blockSize = Math.floor(rawData.length / samples);
          
          for (let i = 0; i < samples; i++) {
            let sum = 0;
            for (let j = 0; j < blockSize; j++) {
              sum += Math.abs(rawData[i * blockSize + j]);
            }
            waveformData.push(sum / blockSize);
          }
          
          // Calculate RMS metrics
          let sumSquares = 0;
          let peak = 0;
          for (let i = 0; i < rawData.length; i++) {
            const abs = Math.abs(rawData[i]);
            sumSquares += rawData[i] * rawData[i];
            if (abs > peak) peak = abs;
          }
          const rms = Math.sqrt(sumSquares / rawData.length);
          const crest = peak / rms;
          
          audioMetrics = {
            avgRms: rms,
            peakRms: peak,
            dynamicRange: crest > 10 ? 'wide' : crest > 5 ? 'moderate' : 'compressed',
            duration: audioBuffer.duration,
          };
          
          audioContext.close();
        } catch (e) {
          console.log('Could not extract waveform:', e);
        }

        // Add user message showing the upload with waveform
        setMessages(prev => [...prev, {
          id: `upload-${Date.now()}`,
          role: 'user',
          content: `Uploaded: **${file.name}**`,
          timestamp: new Date(),
          audioFile: {
            name: file.name,
            url: result.audioUrl,
          },
          waveformData: waveformData.length > 0 ? waveformData : undefined,
          audioMetrics: audioMetrics.duration > 0 ? audioMetrics : undefined,
        }]);

        // Howard asks for song name with encouragement
        setMessages(prev => [...prev, {
          id: `ask-name-${Date.now()}`,
          role: 'assistant',
          content: `Excellent! Your file is uploaded and ready. I can't wait to hear what you've been working on! 🎵

**What's the name of this song?**`,
          timestamp: new Date(),
        }]);

        setChatState('file_uploaded');
        setIsUploading(false);
      };
      reader.readAsDataURL(file);
    } catch (error) {
      console.error('Upload error:', error);
      toast.error('Failed to upload file. Please try again.');
      setIsUploading(false);
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Handle sending message
  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage = inputValue.trim();
    setInputValue('');

    // Add user message
    setMessages(prev => [...prev, {
      id: `user-${Date.now()}`,
      role: 'user',
      content: userMessage,
      timestamp: new Date(),
    }]);

    if (chatState === 'file_uploaded') {
      // User is providing song name
      setSongName(userMessage);
      
      // Ask for context with encouragement
      setMessages(prev => [...prev, {
        id: `ask-context-${Date.now()}`,
        role: 'assistant',
        content: `**"${userMessage}"** - love it! 🎤

Anything I should know before I dive in?

• Recording conditions?
• Intentional style choices?
• Areas you want feedback on?

Or just type **"analyze"** to start!`,
        timestamp: new Date(),
      }]);

      setChatState('awaiting_context');
    } else if (chatState === 'awaiting_context') {
      // User provided context, start analysis
      const context = userMessage.toLowerCase() === 'analyze' ? '' : userMessage;
      setUserContext(context);
      startAnalysis(songName, context);
    } else if (chatState === 'complete') {
      // After analysis, allow follow-up questions with progress telemetry
      setIsSending(true);
      
      // Check if this is a deeper analysis request
      const deeperKeywords = /timestamp|timestamps|comparison|compare|exercises|exercise|micro|phrase|breakdown|metrics|metric|advanced|reference|deeper|more detail|expand|elaborate|yes/i;
      const isDeeperRequest = deeperKeywords.test(userMessage);
      
      // Show progress steps for deeper analysis requests
      if (isDeeperRequest) {
        const deeperSteps: AnalysisStep[] = [
          { id: 'deep-1', label: 'Processing your request...', status: 'pending' },
          { id: 'deep-2', label: 'Reviewing previous analysis...', status: 'pending' },
          { id: 'deep-3', label: 'Generating detailed breakdown...', status: 'pending' },
          { id: 'deep-4', label: 'Preparing extended feedback...', status: 'pending' },
        ];
        setAnalysisSteps(deeperSteps);
        
        // Animate through steps
        for (let i = 0; i < deeperSteps.length; i++) {
          await new Promise(resolve => setTimeout(resolve, 400));
          setAnalysisSteps(prev => prev.map((step, idx) => ({
            ...step,
            status: idx < i ? 'completed' : idx === i ? 'active' : 'pending'
          })));
        }
      }
      
      try {
        const response = await howardChatMutation.mutateAsync({
          userMessage: userMessage,
          mode: 'deep',
        });

        // Mark all steps complete
        if (isDeeperRequest) {
          setAnalysisSteps(prev => prev.map(step => ({ ...step, status: 'completed' as const })));
          setTimeout(() => setAnalysisSteps([]), 1500);
        }

        setMessages(prev => [...prev, {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: typeof response.response === 'string' ? response.response : 'Unable to generate response',
          timestamp: new Date(),
        }]);
      } catch (error) {
        toast.error('Failed to get response');
        setAnalysisSteps([]);
      }
      setIsSending(false);
    } else {
      // Idle state - remind to upload
      setMessages(prev => [...prev, {
        id: `reminder-${Date.now()}`,
        role: 'assistant',
        content: `Please upload an audio file first using the **Upload** button below. I'll then guide you through the analysis process.`,
        timestamp: new Date(),
      }]);
    }
  };

  // Start the analysis with step-by-step progress
  const startAnalysis = async (name: string, context: string) => {
    setChatState('analyzing');
    
    // Initialize analysis steps - more interactive and descriptive
    const steps: AnalysisStep[] = [
      { id: 'upload', label: 'File Uploaded', status: 'pending' },
      { id: 'analyze', label: 'Analyzing Audio', status: 'pending' },
      { id: 'process', label: 'Processing Vocal Patterns', status: 'pending' },
      { id: 'docs', label: 'Checking Coaching Documentation', status: 'pending' },
      { id: 'extract', label: 'Extracting Insights', status: 'pending' },
      { id: 'recommend', label: 'Preparing Recommendations', status: 'pending' },
      { id: 'deliver', label: 'Delivering Results', status: 'pending' },
    ];
    setAnalysisSteps(steps);

    // Add encouraging analyzing message
    setMessages(prev => [...prev, {
      id: `analyzing-${Date.now()}`,
      role: 'assistant',
      content: `Alright, let's hear what you've got! 🎧

Analyzing **"${name}"**...`,
      timestamp: new Date(),
    }]);

    // Simulate step-by-step progress
    const updateStep = (stepId: string, status: 'active' | 'completed', detail?: string) => {
      setAnalysisSteps(prev => prev.map(s => 
        s.id === stepId ? { ...s, status, detail } : s
      ));
    };

    try {
      // Step 1: File Uploaded
      updateStep('upload', 'active');
      await new Promise(r => setTimeout(r, 800));
      updateStep('upload', 'completed', 'Audio file received');

      // Step 2: Analyzing Audio
      updateStep('analyze', 'active');
      await new Promise(r => setTimeout(r, 1500));
      updateStep('analyze', 'completed', 'Waveform and frequency analysis complete');

      // Step 3: Processing Vocal Patterns
      updateStep('process', 'active');
      await new Promise(r => setTimeout(r, 1800));
      updateStep('process', 'completed', 'Pitch, timing, and tone patterns identified');

      // Step 4: Checking Coaching Documentation
      updateStep('docs', 'active');
      await new Promise(r => setTimeout(r, 1200));
      updateStep('docs', 'completed', 'VOXAI Protocol and exercise library consulted');

      // Step 5: Extracting Insights
      updateStep('extract', 'active');
      await new Promise(r => setTimeout(r, 1500));
      updateStep('extract', 'completed', 'Vocal archetype and corrections determined');

      // Step 6: Preparing Recommendations
      updateStep('recommend', 'active');
      await new Promise(r => setTimeout(r, 1000));
      updateStep('recommend', 'completed', 'Exercises and coaching cues selected');

      // Step 7: Delivering Results
      updateStep('deliver', 'active');

      // Now call the actual analysis
      const response = await howardChatMutation.mutateAsync({
        userMessage: `Please analyze this vocal performance using the VOXAI 6-Phase Protocol.

Song: "${name}"
${context ? `User notes: ${context}` : ''}

Provide a complete analysis following this structure:
1. First Listen - One-line summary and perceived vocal archetype
2. Technical Audit - Pitch, timing, tone, technique, emotion, stage presence
3. Quick Fix - Short, body-feel corrections
4. Prescribed Exercise - One elite drill with detailed instructions
5. Emotional Coaching - Intention, character, phrasing guidance
6. Progress Pathway - Next reps, what to listen for, goal of next take`,
        mode: 'deep',
        analysisId: uploadedFile?.analysisId,
      });

      updateStep('deliver', 'completed', 'Analysis complete');

      // Set final analysis
      const analysisText = typeof response.response === 'string' ? response.response : 'Unable to generate analysis';
      setFinalAnalysis(analysisText);
      
      // Store analysisId for phrase breakdown
      if (uploadedFile?.analysisId) {
        setAnalysisId(uploadedFile.analysisId);
      }

      // Add the analysis as a message
      setMessages(prev => [...prev, {
        id: `analysis-${Date.now()}`,
        role: 'assistant',
        content: analysisText,
        timestamp: new Date(),
      }]);
      
      // Auto-scroll to top to show analysis results
      setTimeout(() => {
        if (scrollAreaRef.current) {
          const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
          if (scrollContainer) {
            scrollContainer.scrollTop = 0;
          }
        }
      }, 100);

      // Clear steps after a moment
      setTimeout(() => {
        setAnalysisSteps([]);
      }, 2000);

      setChatState('complete');

      // Add encouraging follow-up message asking about download
      setTimeout(() => {
        setMessages(prev => [...prev, {
          id: `followup-${Date.now()}`,
          role: 'assistant',
          content: `---

**Great work putting yourself out there!** 🌟

Remember: every singer you admire started exactly where you are. The fact that you're analyzing your voice and seeking feedback puts you ahead of most.

Want to go deeper? Tap a button below or ask me anything:`,
          timestamp: new Date(),
          quickReplies: [
            { label: '📝 Would you like to analyze this phrase by phrase?', value: 'Give me a phrase-by-phrase breakdown' },
          ],
        }]);
      }, 500);

    } catch (error) {
      console.error('Analysis error:', error);
      toast.error('Analysis failed. Please try again.');
      setChatState('idle');
      setAnalysisSteps([]);
    }
  };

  // Save analysis as text file
  const handleSaveAnalysis = () => {
    if (!finalAnalysis) {
      toast.error('No analysis to save');
      return;
    }

    const content = `VOX AI Vocal Analysis
Generated: ${new Date().toLocaleString()}
Song: ${songName}
${userContext ? `Notes: ${userContext}` : ''}

${'='.repeat(50)}

${finalAnalysis}

${'='.repeat(50)}

Analyzed by Howard - VOX AI Elite Vocal Coach
https://aaronellis.au
`;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `voxai-analysis-${songName.replace(/[^a-z0-9]/gi, '-').toLowerCase()}-${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('Analysis saved!');
  };

  // Handle quick reply button clicks
  const handleQuickReply = async (value: string) => {
    // Handle download action
    if (value === '__download__') {
      handleSaveAnalysis();
      return;
    }

    // Add user message
    setMessages(prev => [...prev, {
      id: `user-${Date.now()}`,
      role: 'user',
      content: value,
      timestamp: new Date(),
    }]);

    // Clear quick replies from the message that triggered this
    setMessages(prev => prev.map(msg => 
      msg.quickReplies ? { ...msg, quickReplies: undefined } : msg
    ));

    // Trigger follow-up response
    setIsSending(true);
    try {
      // Check if this is a phrase-by-phrase breakdown request
      const isPhraseBreakdown = value.includes('phrase') || value.includes('breakdown');
      
      if (isPhraseBreakdown) {
        // Show reanalyzing message
        setMessages(prev => [...prev, {
          id: `reanalyzing-${Date.now()}`,
          role: 'assistant',
          content: 'Reanalyzing now, won\'t be a moment...',
          timestamp: new Date(),
        }]);
        
        // Call phrase breakdown endpoint
        if (finalAnalysis && analysisId) {
          const breakdownResponse = await phraseBreakdownMutation.mutateAsync({
            analysisId,
            userMessage: value,
          });
          
          // Remove the reanalyzing message and add the breakdown
          setMessages(prev => {
            const filtered = prev.filter(msg => msg.id !== `reanalyzing-${Date.now()}`);
            return [...filtered, {
              id: `breakdown-${Date.now()}`,
              role: 'assistant',
              content: breakdownResponse.response,
              timestamp: new Date(),
            }];
          });
          
          setIsSending(false);
          return;
        }
      }
      
      let messageToSend = value;
      
      if (finalAnalysis) {
        messageToSend = `The user said "${value}" - they want more detailed analysis.

Previous analysis for "${songName}":
${finalAnalysis}

Please provide an EXTENDED DEEP DIVE analysis that includes:
1. **TIMESTAMP-SPECIFIC OBSERVATIONS** - Call out exact moments (e.g., "At 0:45...", "From 1:20-1:35...")
2. **ADVANCED METRIC ANALYSIS** - Detailed breakdown of crest factor, dynamic range, formant characteristics
3. **COMPARISON TO REFERENCE** - How this performance compares to the original artist or similar professional performances
4. **EXTENDED EXERCISE PRESCRIPTIONS** - 3-4 additional exercises with specific instructions, not just one
5. **MICRO-CORRECTIONS** - Small adjustments that could make a big difference

Be specific, detailed, and actionable. Use timestamps where possible.`;
      }

      const response = await howardChatMutation.mutateAsync({
        userMessage: messageToSend,
        mode: 'deep',
      });

      // Extract text from response
      let responseText = '';
      if (typeof response.response === 'string') {
        responseText = response.response;
      } else if (Array.isArray(response.response)) {
        responseText = response.response
          .filter((item): item is { type: 'text'; text: string } => item.type === 'text')
          .map(item => item.text)
          .join('\n');
      }

      setMessages(prev => [...prev, {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: responseText,
        timestamp: new Date(),
      }]);
    } catch (error) {
      console.error('Quick reply error:', error);
      toast.error('Failed to get response. Please try again.');
    } finally {
      setIsSending(false);
    }
  };

  // Reset chat
  const handleNewAnalysis = () => {
    setMessages([{
      id: 'welcome',
      role: 'assistant',
      content: `Ready for another analysis! Upload your next audio file.`,
      timestamp: new Date(),
    }]);
    setChatState('idle');
    setUploadedFile(null);
    setSongName('');
    setUserContext('');
    setFinalAnalysis(null);
    setAnalysisSteps([]);
  };

  // Voice input handler
  const toggleVoiceInput = () => {
    // Check if speech recognition is supported
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      toast.error('Voice input is not supported in this browser');
      return;
    }

    if (isListening) {
      // Stop listening
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    // Start listening
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results)
        .map((result: any) => result[0].transcript)
        .join('');
      setInputValue(transcript);
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      if (event.error === 'not-allowed') {
        toast.error('Microphone access denied. Please enable it in your browser settings.');
      } else {
        toast.error('Voice input error. Please try again.');
      }
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  // Auth loading
  if (authLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  // Not authenticated
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <VoxAINavigation />
        <div className="flex-1 flex items-center justify-center p-4 pt-20">
          <div className="text-center space-y-6 max-w-md">
            <div className="w-20 h-20 mx-auto rounded-full bg-primary/20 flex items-center justify-center">
              <Mic className="w-10 h-10 text-primary" />
            </div>
            <h1 className="text-2xl font-bold">VOX AI Vocal Coach</h1>
            <p className="text-muted-foreground">
              Get professional vocal analysis and coaching from Howard, your elite AI vocal coach.
            </p>
            <Button asChild className="bg-primary hover:bg-primary/80">
              <a href={getLoginUrl()}>Sign In to Start</a>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Loading invite status
  if (inviteCheck.isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  // Not invited - show subscription options
  if (!inviteCheck.data?.isInvited) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <VoxAINavigation />
        <div className="flex-1 flex items-center justify-center p-4 pt-20">
          <div className="text-center space-y-6 max-w-lg">
            <div className="w-20 h-20 mx-auto rounded-full bg-primary/20 flex items-center justify-center">
              <Mic className="w-10 h-10 text-primary" />
            </div>
            <h1 className="text-2xl font-bold">Welcome to VOX AI</h1>
            <p className="text-muted-foreground">
              Get professional vocal analysis and coaching from Howard, your elite AI vocal coach.
            </p>
            
            {/* Subscription tiers */}
            <div className="grid gap-4 mt-6">
              {/* Free tier */}
              <div className="p-4 rounded-lg border border-border bg-card text-left">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="font-semibold">Free</h3>
                  <span className="text-lg font-bold">$0</span>
                </div>
                <p className="text-sm text-muted-foreground mb-3">3 analyses per month</p>
                <Button asChild className="w-full" variant="outline">
                  <a href="/subscription">Get Started Free</a>
                </Button>
              </div>
              
              {/* Basic tier */}
              <div className="p-4 rounded-lg border border-primary/50 bg-card text-left">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="font-semibold">Basic</h3>
                  <span className="text-lg font-bold">$5 <span className="text-sm font-normal text-muted-foreground">AUD/mo</span></span>
                </div>
                <p className="text-sm text-muted-foreground mb-3">10 analyses per month + $0.99 per extra</p>
                <Button asChild className="w-full bg-primary hover:bg-primary/80">
                  <a href="/subscription">Subscribe to Basic</a>
                </Button>
              </div>
              
              {/* Pro tier */}
              <div className="p-4 rounded-lg border border-[var(--holo-cyan)]/50 bg-card text-left relative overflow-hidden">
                <div className="absolute top-0 right-0 bg-[var(--holo-cyan)] text-black text-xs px-2 py-0.5 rounded-bl">Popular</div>
                <div className="flex justify-between items-center mb-2">
                  <h3 className="font-semibold">Pro</h3>
                  <span className="text-lg font-bold">$12 <span className="text-sm font-normal text-muted-foreground">AUD/mo</span></span>
                </div>
                <p className="text-sm text-muted-foreground mb-3">50 analyses per month + $0.99 per extra</p>
                <Button asChild className="w-full bg-[var(--holo-cyan)] text-black hover:bg-[var(--holo-cyan)]/80">
                  <a href="/subscription">Subscribe to Pro</a>
                </Button>
              </div>
            </div>
            
            <Button asChild variant="ghost" size="sm">
              <a href="/">Return to Home</a>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <VoxAINavigation />
      
      {/* Upload Animation Overlay */}
      {isUploading && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center">
          <div className="text-center space-y-4 p-8 rounded-2xl bg-card border border-border shadow-xl">
            <div className="relative w-20 h-20 mx-auto">
              <div className="absolute inset-0 rounded-full border-4 border-primary/20" />
              <div className="absolute inset-0 rounded-full border-4 border-primary border-t-transparent animate-spin" />
              <FileAudio className="absolute inset-0 m-auto w-8 h-8 text-primary" />
            </div>
            <div>
              <p className="text-lg font-semibold">Uploading your track...</p>
              <p className="text-sm text-muted-foreground">This may take a moment for larger files</p>
            </div>
          </div>
        </div>
      )}
      
      <div className="flex-1 flex flex-col pt-0 pb-[180px] max-w-4xl mx-auto w-full">
        {/* Messages area */}
        <ScrollArea className="flex-1 p-4" ref={scrollAreaRef}>
          <div className="space-y-4 pb-4 pt-20">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
              >
                <div className={`w-6 h-6 sm:w-8 sm:h-8 rounded-full flex items-center justify-center shrink-0 ${
                  message.role === 'user' 
                    ? 'bg-primary/20' 
                    : 'bg-[var(--holo-cyan)]/20'
                }`}>
                  {message.role === 'user' ? (
                    <User className="w-3 h-3 sm:w-4 sm:h-4 text-primary" />
                  ) : (
                    <Bot className="w-3 h-3 sm:w-4 sm:h-4 text-[var(--holo-cyan)]" />
                  )}
                </div>
                <div className={`flex-1 max-w-[80%] sm:max-w-[85%] ${message.role === 'user' ? 'text-right' : ''}`}>
                  <div className={`inline-block rounded-2xl px-3 py-2 sm:px-4 sm:py-3 text-sm sm:text-base ${
                    message.role === 'user'
                      ? 'bg-primary/20 text-foreground'
                      : 'bg-muted/50'
                  }`}>
                    {message.audioFile && (
                      <div className="mb-3 p-2 sm:p-3 rounded-lg bg-background/50 w-full max-w-full overflow-hidden">
                        <div className="flex items-center gap-2 mb-2">
                          <FileAudio className="w-4 h-4 text-[var(--holo-cyan)] shrink-0" />
                          <span className="text-xs sm:text-sm font-medium truncate flex-1 min-w-0">{message.audioFile.name}</span>
                        </div>
                        
                        {/* Studio Monitor Visualization */}
                        {message.waveformData && message.waveformData.length > 0 ? (
                          <StudioMonitor
                            audioUrl={message.audioFile.url}
                            waveformData={message.waveformData}
                            duration={message.audioMetrics?.duration || 0}
                            avgRms={message.audioMetrics?.avgRms}
                            peakRms={message.audioMetrics?.peakRms}
                            dynamicRange={message.audioMetrics?.dynamicRange}
                          />
                        ) : (
                          <audio 
                            src={message.audioFile.url} 
                            controls 
                            className="h-8 w-full"
                          />
                        )}
                      </div>
                    )}
                    <div className="prose prose-invert prose-xs sm:prose-sm max-w-none break-words">
                      <Streamdown>{message.content}</Streamdown>
                    </div>
                    {/* Quick Reply Buttons */}
                    {message.quickReplies && message.quickReplies.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-border/30">
                        {message.quickReplies.map((reply, idx) => (
                          <Button
                            key={idx}
                            variant="outline"
                            size="sm"
                            className="text-xs bg-[var(--holo-cyan)]/10 border-[var(--holo-cyan)]/30 hover:bg-[var(--holo-cyan)]/20 hover:border-[var(--holo-cyan)]/50"
                            onClick={() => handleQuickReply(reply.value)}
                            disabled={isSending}
                          >
                            {reply.label}
                          </Button>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className={`text-xs text-muted-foreground mt-1 ${message.role === 'user' ? 'text-right' : ''}`}>
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            ))}

            {/* Analysis Progress Steps */}
            {analysisSteps.length > 0 && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-[var(--holo-cyan)]/20 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4 text-[var(--holo-cyan)]" />
                </div>
                <div className="flex-1 bg-muted/50 rounded-2xl px-4 py-3">
                  <div className="text-sm font-medium mb-3 flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-[var(--holo-cyan)]" />
                    Analyzing your performance...
                  </div>
                  <div className="space-y-2">
                    {analysisSteps.map((step) => (
                      <div key={step.id} className="flex items-center gap-2 text-sm">
                        {step.status === 'completed' ? (
                          <CheckCircle2 className="w-4 h-4 text-green-500" />
                        ) : step.status === 'active' ? (
                          <Loader2 className="w-4 h-4 animate-spin text-[var(--holo-cyan)]" />
                        ) : (
                          <Circle className="w-4 h-4 text-muted-foreground" />
                        )}
                        <span className={step.status === 'pending' ? 'text-muted-foreground' : ''}>
                          {step.label}
                        </span>
                        {step.detail && (
                          <span className="text-xs text-muted-foreground">- {step.detail}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {/* Input area - fixed at bottom */}
        <div className="fixed bottom-0 left-0 right-0 border-t border-border/50 p-4 bg-background/95 backdrop-blur-lg z-40">
          <div className="max-w-4xl mx-auto">
          {/* Quick-reply buttons when awaiting context */}
          {chatState === 'awaiting_context' && (
            <div className="flex gap-2 mb-3 flex-wrap">
              <Button
                variant="default"
                size="sm"
                onClick={() => {
                  setUserContext('');
                  startAnalysis(songName, '');
                }}
                className="bg-[var(--holo-cyan)] hover:bg-[var(--holo-cyan)]/80 text-black font-medium"
              >
                <CheckCircle2 className="w-4 h-4 mr-2" />
                Yes, analyze!
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  // Focus the input for adding notes
                  const input = document.querySelector('input[type="text"]') as HTMLInputElement;
                  if (input) input.focus();
                }}
                className="border-[var(--holo-pink)]/50 text-[var(--holo-pink)]"
              >
                <FileAudio className="w-4 h-4 mr-2" />
                Add notes first
              </Button>
            </div>
          )}

          {/* Action buttons when analysis is complete */}
          {chatState === 'complete' && finalAnalysis && (
            <div className="flex gap-2 mb-3 flex-wrap">
              <Button
                variant="outline"
                size="sm"
                onClick={handleSaveAnalysis}
                className="border-[var(--holo-cyan)]/50"
              >
                <Download className="w-4 h-4 mr-2" />
                Save as Text
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleNewAnalysis}
              >
                <Music2 className="w-4 h-4 mr-2" />
                New Analysis
              </Button>
            </div>
          )}

          <div className="flex gap-2">
            {/* File upload button */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".wav,.mp3,.m4a,.aac,audio/*"
              className="hidden"
            />
            <Button
              variant="outline"
              size="icon"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading || chatState === 'analyzing'}
              className="shrink-0"
            >
              {isUploading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Upload className="w-4 h-4" />
              )}
            </Button>

            {/* Text input */}
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
              placeholder={
                chatState === 'idle' ? 'Upload a file to get started...' :
                chatState === 'file_uploaded' ? 'Enter the song name...' :
                chatState === 'awaiting_context' ? 'Any notes? Or say "analyze"...' :
                chatState === 'analyzing' ? 'Analyzing...' :
                'Ask a follow-up question...'
              }
              disabled={chatState === 'analyzing' || isSending}
              className="flex-1"
            />

            {/* Voice input button */}
            <Button
              variant="outline"
              size="icon"
              onClick={toggleVoiceInput}
              disabled={chatState === 'analyzing' || isSending || chatState === 'idle'}
              className={`shrink-0 ${isListening ? 'bg-red-500/20 border-red-500 animate-pulse' : ''}`}
              title={isListening ? 'Stop listening' : 'Voice input'}
            >
              {isListening ? (
                <MicOff className="w-4 h-4 text-red-500" />
              ) : (
                <Mic className="w-4 h-4" />
              )}
            </Button>

            {/* Send button */}
            <Button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || chatState === 'analyzing' || isSending}
              className="shrink-0 bg-primary hover:bg-primary/80"
            >
              {isSending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </div>

          <p className="text-xs text-muted-foreground mt-2 text-center">
            Supported: WAV, MP3, M4A, AAC • Max 100MB
          </p>
          </div>
        </div>
      </div>
    </div>
  );
}
