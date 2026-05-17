# PHASE 09 — Frontend: Complete Instant Post Flow UI

## Phase Goal
Build the complete end-to-end Instant Post Mode UI. A user fills in project details → clicks Generate → sees a step-by-step loading screen → gets their LinkedIn post with copy, edit, and publish buttons. All output tabs (LinkedIn, Resume Bullet, Portfolio Summary) are rendered. The Recruiter Score panel is displayed after generation.

---

## Features Implemented
- Instant Mode Page (`/dashboard/instant`)
- Step 1: Project Input Form (required + collapsible optional fields)
- Step 2: AI Analysis loading animation (step-by-step messages)
- Step 3: Output tabs — LinkedIn Post / Resume Bullet / Portfolio Summary
- Recruiter Visibility Score panel (mock scoring from post metadata)
- Copy, Edit, Regenerate, Publish to LinkedIn actions
- "Schedule this post instead" button (bridges to Growth Automation)
- Error state handling (rate limit, AI timeout)
- `job_id` persisted in URL for refresh recovery
- Toast notifications for copy/publish actions

---

## Technical Architecture

```
src/app/dashboard/instant/
├── page.tsx                     ← Main instant flow page (state machine)
└── components/
    ├── StepIndicator.tsx        ← Step 1/2/3 progress bar
    ├── ProjectInputForm.tsx     ← Required + optional fields
    ├── GenerationLoader.tsx     ← Animated step-by-step loading
    ├── OutputPanel.tsx          ← Tabs: LinkedIn / Resume / Portfolio
    ├── RecruiterScore.tsx       ← Score display panel
    └── PostActions.tsx          ← Copy / Edit / Publish / Schedule
```

---

## Page State Machine (`src/app/dashboard/instant/page.tsx`)
```tsx
'use client';
import { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import StepIndicator from './components/StepIndicator';
import ProjectInputForm from './components/ProjectInputForm';
import GenerationLoader from './components/GenerationLoader';
import OutputPanel from './components/OutputPanel';
import { startInstantGeneration } from '@/lib/generation-api';
import { useGenerationJob } from '@/hooks/useGenerationJob';
import { useToast } from '@/components/ui/use-toast';

type Step = 'input' | 'loading' | 'output';

export default function InstantPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { toast } = useToast();

  // Recover from refresh: check URL for jobId
  const [step, setStep] = useState<Step>('input');
  const [jobId, setJobId] = useState<string | null>(
    searchParams.get('jobId') || null
  );
  const [projectId, setProjectId] = useState<string | null>(null);
  const [inputData, setInputData] = useState<any>(null);

  // Poll job status
  const { job, loading: polling } = useGenerationJob(
    step === 'loading' ? jobId : null
  );

  // Transition to output when job completes
  useEffect(() => {
    if (!job) return;
    if (job.status === 'completed') {
      setStep('output');
    } else if (job.status === 'failed') {
      toast({
        title: 'Generation failed',
        description: job.message || 'Please try again.',
        variant: 'destructive',
      });
      setStep('input');
      setJobId(null);
      router.replace('/dashboard/instant');
    }
  }, [job]);

  // Persist jobId in URL for refresh recovery
  useEffect(() => {
    if (jobId && step === 'loading') {
      router.replace(`/dashboard/instant?jobId=${jobId}`);
    }
  }, [jobId, step]);

  const handleGenerate = async (formData: any) => {
    setInputData(formData);
    try {
      const res = await startInstantGeneration({
        project_id: formData.project_id,
        tone: formData.tone || 'professional',
        target_audience: formData.target_audience || 'recruiters',
      });
      setJobId(res.job_id);
      setStep('loading');
    } catch (err: any) {
      const code = err.response?.data?.code;
      if (code === 'RATE_LIMIT_EXCEEDED') {
        toast({
          title: 'Daily limit reached',
          description: 'Free plan: 5 generations/day. Upgrade for unlimited.',
          variant: 'destructive',
        });
      } else {
        toast({ title: 'Error', description: 'Something went wrong.', variant: 'destructive' });
      }
    }
  };

  const handleRegenerate = async () => {
    if (!inputData) return;
    setStep('loading');
    await handleGenerate(inputData);
  };

  return (
    <div className="max-w-3xl mx-auto py-4">
      <StepIndicator current={step} />

      <div className="mt-8">
        {step === 'input' && (
          <ProjectInputForm onSubmit={handleGenerate} />
        )}
        {step === 'loading' && (
          <GenerationLoader />
        )}
        {step === 'output' && job?.posts?.[0] && (
          <OutputPanel
            post={job.posts[0]}
            onRegenerate={handleRegenerate}
            onSchedule={() => router.push(
              `/dashboard/schedule?projectId=${job.posts[0]?.project_id}`
            )}
          />
        )}
      </div>
    </div>
  );
}
```

---

## Step Indicator (`src/app/dashboard/instant/components/StepIndicator.tsx`)
```tsx
import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

const STEPS = [
  { id: 'input', label: 'Project Info' },
  { id: 'loading', label: 'AI Analysis' },
  { id: 'output', label: 'Your Content' },
];

export default function StepIndicator({ current }: { current: string }) {
  const currentIndex = STEPS.findIndex(s => s.id === current);

  return (
    <div className="flex items-center gap-0">
      {STEPS.map((step, i) => {
        const isDone = i < currentIndex;
        const isActive = i === currentIndex;
        return (
          <div key={step.id} className="flex items-center">
            <div className="flex flex-col items-center">
              <div className={cn(
                'w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold border-2 transition-colors',
                isDone && 'bg-primary border-primary text-primary-foreground',
                isActive && 'border-primary text-primary',
                !isDone && !isActive && 'border-muted-foreground/30 text-muted-foreground'
              )}>
                {isDone ? <Check className="w-4 h-4" /> : i + 1}
              </div>
              <span className={cn(
                'text-xs mt-1 whitespace-nowrap',
                isActive ? 'text-primary font-medium' : 'text-muted-foreground'
              )}>
                {step.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={cn(
                'h-px flex-1 min-w-[40px] mx-2 -mt-4 transition-colors',
                isDone ? 'bg-primary' : 'bg-border'
              )} />
            )}
          </div>
        );
      })}
    </div>
  );
}
```

---

## Project Input Form (`src/app/dashboard/instant/components/ProjectInputForm.tsx`)
```tsx
'use client';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ChevronDown, ChevronUp, Zap } from 'lucide-react';
import { createProject } from '@/lib/projects-api';

interface Props { onSubmit: (data: any) => void; }

export default function ProjectInputForm({ onSubmit }: Props) {
  const [form, setForm] = useState({
    title: '', github_url: '', problem_solved: '',
    tech_stack: '', results_impact: '', features: '',
    tone: 'professional', target_audience: 'recruiters',
  });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const update = (key: string) => (e: any) =>
    setForm(p => ({ ...p, [key]: e.target.value }));

  const handleSubmit = async () => {
    setError('');
    if (!form.title || !form.problem_solved || !form.tech_stack) {
      setError('Please fill in the required fields.');
      return;
    }
    setLoading(true);
    try {
      // Create project first, then generate
      const project = await createProject({
        title: form.title,
        github_url: form.github_url || undefined,
        problem_solved: form.problem_solved,
        tech_stack: form.tech_stack.split(',').map(s => s.trim()).filter(Boolean),
        results_impact: form.results_impact || undefined,
        features: form.features
          ? form.features.split(',').map(s => s.trim()).filter(Boolean)
          : undefined,
      });
      onSubmit({ project_id: project.id, tone: form.tone, target_audience: form.target_audience });
    } catch (err: any) {
      setError(err.response?.data?.message || 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-1">Tell us about your project</h2>
        <p className="text-muted-foreground">Fill in the details and we'll handle the rest.</p>
      </div>

      {/* Required Fields */}
      <div className="space-y-4">
        <div>
          <Label>Project Title <span className="text-destructive">*</span></Label>
          <Input value={form.title} onChange={update('title')} placeholder="e.g. AgriLenses" className="mt-1.5" />
        </div>
        <div>
          <Label>GitHub Repository (optional)</Label>
          <Input value={form.github_url} onChange={update('github_url')} placeholder="https://github.com/you/project" className="mt-1.5" />
        </div>
        <div>
          <Label>Problem Solved <span className="text-destructive">*</span></Label>
          <Textarea
            value={form.problem_solved}
            onChange={update('problem_solved')}
            placeholder="What problem does your project solve? Be specific."
            rows={3}
            className="mt-1.5"
          />
        </div>
        <div>
          <Label>Tech Stack <span className="text-destructive">*</span></Label>
          <Input value={form.tech_stack} onChange={update('tech_stack')} placeholder="Python, FastAPI, React, MongoDB (comma-separated)" className="mt-1.5" />
        </div>
      </div>

      {/* Optional Fields — Collapsible */}
      <div>
        <button
          type="button"
          onClick={() => setShowAdvanced(v => !v)}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          {showAdvanced ? 'Hide' : 'Show'} optional fields (results, features, tone)
        </button>

        {showAdvanced && (
          <div className="mt-4 space-y-4 border rounded-xl p-4 bg-muted/30">
            <div>
              <Label>Results / Impact</Label>
              <Input value={form.results_impact} onChange={update('results_impact')} placeholder="e.g. 92% accuracy, 30% reduction in crop loss" className="mt-1.5" />
            </div>
            <div>
              <Label>Key Features (comma-separated)</Label>
              <Input value={form.features} onChange={update('features')} placeholder="Real-time detection, Mobile-friendly UI" className="mt-1.5" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Tone</Label>
                <Select onValueChange={v => setForm(p => ({ ...p, tone: v }))} defaultValue="professional">
                  <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {['professional', 'casual', 'storytelling', 'technical', 'inspiring'].map(t => (
                      <SelectItem key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Target Audience</Label>
                <Select onValueChange={v => setForm(p => ({ ...p, target_audience: v }))} defaultValue="recruiters">
                  <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {['recruiters', 'developers', 'students', 'startup_founders'].map(a => (
                      <SelectItem key={a} value={a}>{a.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Button onClick={handleSubmit} disabled={loading} size="lg" className="w-full gap-2">
        <Zap className="w-4 h-4" />
        {loading ? 'Preparing...' : 'Generate Content'}
      </Button>
    </div>
  );
}
```

---

## Generation Loader (`src/app/dashboard/instant/components/GenerationLoader.tsx`)
```tsx
'use client';
import { useState, useEffect } from 'react';
import { CheckCircle, Loader2 } from 'lucide-react';

const STEPS = [
  'Understanding your project deeply...',
  'Extracting key achievements and impact...',
  'Choosing the best content angle...',
  'Crafting your opening hook...',
  'Writing recruiter-friendly content...',
  'Humanizing the output...',
];

export default function GenerationLoader() {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentStep(s => (s < STEPS.length - 1 ? s + 1 : s));
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex flex-col items-center py-16 space-y-10">
      <div className="relative">
        <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center">
          <Loader2 className="w-10 h-10 text-primary animate-spin" />
        </div>
      </div>

      <div className="text-center space-y-2">
        <h3 className="text-xl font-semibold">Turning your project into recruiter-friendly content</h3>
        <p className="text-muted-foreground text-sm">This takes about 15–30 seconds.</p>
      </div>

      {/* Step list */}
      <div className="space-y-3 w-full max-w-sm">
        {STEPS.map((step, i) => (
          <div key={i} className={`flex items-center gap-3 text-sm transition-all ${
            i < currentStep ? 'text-foreground' :
            i === currentStep ? 'text-primary font-medium' :
            'text-muted-foreground/40'
          }`}>
            {i < currentStep
              ? <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
              : i === currentStep
              ? <Loader2 className="w-4 h-4 animate-spin text-primary shrink-0" />
              : <div className="w-4 h-4 rounded-full border border-muted-foreground/30 shrink-0" />
            }
            {step}
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Output Panel (`src/app/dashboard/instant/components/OutputPanel.tsx`)
```tsx
'use client';
import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Copy, Check, RefreshCw, Linkedin, Calendar } from 'lucide-react';
import RecruiterScore from './RecruiterScore';
import { useToast } from '@/components/ui/use-toast';
import api from '@/lib/api';

interface Props {
  post: any;
  onRegenerate: () => void;
  onSchedule: () => void;
}

export default function OutputPanel({ post, onRegenerate, onSchedule }: Props) {
  const [content, setContent] = useState(post.content);
  const [copied, setCopied] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const { toast } = useToast();

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    toast({ title: 'Copied to clipboard!' });
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePublish = async () => {
    setPublishing(true);
    try {
      await api.post(`/publish/${post.id}`);
      toast({ title: '🎉 Published to LinkedIn!' });
    } catch (err: any) {
      const msg = err.response?.data?.message || 'Failed to publish.';
      toast({ title: 'Publish failed', description: msg, variant: 'destructive' });
    } finally {
      setPublishing(false);
    }
  };

  // Generate resume bullet and portfolio summary from post data (derived from content)
  const resumeBullet = `• Built ${post.angle?.replace('_', ' ')} project using ${post.tone} approach — view full details on LinkedIn.`;
  const portfolioSummary = `This project demonstrates ${post.angle?.replace('_', ' ')} skills. The AI-generated LinkedIn post captures the technical depth and business impact.`;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Your Content</h2>
        <Button variant="outline" size="sm" onClick={onRegenerate} className="gap-2">
          <RefreshCw className="w-4 h-4" />
          Regenerate
        </Button>
      </div>

      {/* Recruiter Score */}
      <RecruiterScore post={post} />

      {/* Output Tabs */}
      <Tabs defaultValue="linkedin">
        <TabsList className="w-full">
          <TabsTrigger value="linkedin" className="flex-1">LinkedIn Post</TabsTrigger>
          <TabsTrigger value="resume" className="flex-1">Resume Bullet</TabsTrigger>
          <TabsTrigger value="portfolio" className="flex-1">Portfolio Summary</TabsTrigger>
        </TabsList>

        <TabsContent value="linkedin" className="mt-4">
          <Textarea
            value={content}
            onChange={e => setContent(e.target.value)}
            className="min-h-[320px] text-sm font-mono leading-relaxed"
          />
          <div className="flex flex-wrap gap-3 mt-4">
            <Button onClick={handleCopy} variant="outline" className="gap-2">
              {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
              {copied ? 'Copied!' : 'Copy'}
            </Button>
            <Button
              onClick={handlePublish}
              disabled={publishing || post.status === 'posted'}
              className="gap-2 bg-[#0077B5] hover:bg-[#006097]"
            >
              <Linkedin className="w-4 h-4" />
              {post.status === 'posted' ? 'Published ✓' : publishing ? 'Publishing...' : 'Post to LinkedIn'}
            </Button>
            <Button onClick={onSchedule} variant="outline" className="gap-2">
              <Calendar className="w-4 h-4" />
              Schedule instead
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="resume" className="mt-4">
          <div className="border rounded-xl p-5 bg-muted/30 min-h-[160px]">
            <p className="text-sm leading-relaxed font-mono">{resumeBullet}</p>
          </div>
          <Button onClick={() => navigator.clipboard.writeText(resumeBullet)} variant="outline" className="mt-3 gap-2">
            <Copy className="w-4 h-4" /> Copy bullet
          </Button>
        </TabsContent>

        <TabsContent value="portfolio" className="mt-4">
          <div className="border rounded-xl p-5 bg-muted/30 min-h-[160px]">
            <p className="text-sm leading-relaxed">{portfolioSummary}</p>
          </div>
          <Button onClick={() => navigator.clipboard.writeText(portfolioSummary)} variant="outline" className="mt-3 gap-2">
            <Copy className="w-4 h-4" /> Copy summary
          </Button>
        </TabsContent>
      </Tabs>

      <p className="text-xs text-muted-foreground">
        Angle: <span className="font-medium">{post.angle?.replace('_', ' ')}</span>
        {' · '}Prompt version: <span className="font-medium">{post.prompt_version}</span>
      </p>
    </div>
  );
}
```

---

## Recruiter Score (`src/app/dashboard/instant/components/RecruiterScore.tsx`)
```tsx
'use client';

const SCORES = [
  { label: 'Clarity', key: 'clarity', max: 25 },
  { label: 'Recruiter Appeal', key: 'appeal', max: 25 },
  { label: 'Technical Depth', key: 'depth', max: 25 },
  { label: 'Engagement Potential', key: 'engagement', max: 25 },
];

function deriveScore(post: any): Record<string, number> {
  // Deterministic mock scoring derived from content length, angle, prompt_version
  const base = post.content?.length > 500 ? 20 : 15;
  return {
    clarity: base + 4,
    appeal: base + 2,
    depth: post.angle === 'technical_breakdown' ? base + 5 : base,
    engagement: base + 3,
  };
}

export default function RecruiterScore({ post }: { post: any }) {
  const scores = deriveScore(post);
  const total = Object.values(scores).reduce((a: number, b) => a + (b as number), 0);

  return (
    <div className="border rounded-xl p-5 bg-gradient-to-br from-primary/5 to-background">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">Recruiter Visibility Score</h3>
        <div className="text-3xl font-extrabold text-primary">{total}<span className="text-base font-normal text-muted-foreground">/100</span></div>
      </div>
      <div className="space-y-3">
        {SCORES.map(s => {
          const score = scores[s.key] as number;
          const pct = Math.round((score / s.max) * 100);
          return (
            <div key={s.key}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-muted-foreground">{s.label}</span>
                <span className="font-medium">{score}/{s.max}</span>
              </div>
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${pct}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

---

## Security Considerations
- `job_id` in URL is not a secret — job ownership is enforced server-side
- LinkedIn publish button disabled once `status === 'posted'` to prevent double-posting
- All API calls go through authenticated `api.ts` client (Bearer token in headers)

---

## Environment Variables
No new variables.

---

## Packages to Install
```bash
npx shadcn-ui@latest add tabs textarea toast use-toast
```

---

## Implementation Steps (Exact Order)

1. Add Shadcn `tabs`, `textarea`, `toast` components
2. Create `StepIndicator` component
3. Create `ProjectInputForm` with required + collapsible advanced fields
4. Create `GenerationLoader` animated step component
5. Create `RecruiterScore` panel
6. Create `OutputPanel` with all 3 tabs + copy/publish/schedule buttons
7. Create main `page.tsx` with state machine
8. Add `useGenerationJob` polling hook (Phase 05)
9. Wire `onSchedule` → navigates to `/dashboard/schedule?projectId=...`
10. Test full flow: input → generate → loading → output
11. Test copy button → clipboard works
12. Test publish → LinkedIn post appears
13. Test regenerate → new generation starts
14. Test refresh during loading → `jobId` in URL resumes polling
15. Commit: `git commit -m "Phase 09: Instant Post flow UI complete"`

---

## Edge Cases
- User refreshes during loading → URL has `?jobId=` → polling resumes
- Generation fails → toast shown → user returned to input form
- Publish without LinkedIn connected → 400 from backend → toast with "Connect LinkedIn first"
- Very long generated post → Textarea scrolls, LinkedIn formatter truncates at 3000 chars
- Regenerate mid-output → new `job_id` replaces old one, step resets to `loading`

---

## Deliverables / Checklist

- [ ] `/dashboard/instant` page renders
- [ ] Step indicator shows correct step (1, 2, 3)
- [ ] Required fields validated before submit
- [ ] Optional fields collapse/expand correctly
- [ ] "Generate Content" button creates project + triggers generation
- [ ] Loading screen shows animated step-by-step messages
- [ ] Output renders with LinkedIn post content
- [ ] Recruiter Score panel shows with breakdown bars
- [ ] LinkedIn tab: copy, edit, publish, schedule buttons all work
- [ ] Resume Bullet tab: renders + copy works
- [ ] Portfolio Summary tab: renders + copy works
- [ ] Refresh during loading → polling resumes via URL `jobId`
- [ ] Error toast shown on rate limit / AI failure
- [ ] Publish button disabled after `posted` status

---

## Definition of Completion
A user can fill in project details, click Generate, watch the loading steps, and see a full LinkedIn post with score panel. Copy, Edit, and Publish to LinkedIn all work. Switching tabs shows Resume Bullet and Portfolio Summary. Refreshing during generation resumes correctly via URL state.