# PHASE 10 — Frontend: Growth Automation & Content Calendar UI

## Phase Goal
Build the complete Growth Automation mode UI. A user selects a project, configures their content strategy (post count, interval, tone, audience, start date), triggers batch generation, and sees a Content Calendar with all scheduled posts. Posts can be viewed, edited, rescheduled, and cancelled.

---

## Features Implemented
- Growth Automation Page (`/dashboard/schedule`)
- Multi-step form: Project Selection → Content Strategy → Schedule Config
- Batch generation job polling
- Content Calendar (list view + visual grid)
- Scheduled post card: shows content preview, time, status, actions
- Reschedule post (datetime picker)
- Cancel post (with confirmation)
- "Post now" override for scheduled posts
- Empty state with CTA to create first schedule

---

## Technical Architecture

```
src/app/dashboard/schedule/
├── page.tsx                         ← Main schedule page state machine
└── components/
    ├── ScheduleStepIndicator.tsx    ← Steps: Project → Strategy → Schedule
    ├── ProjectSelector.tsx          ← Pick existing project or create new
    ├── ContentStrategyForm.tsx      ← Tone, audience, style, goal
    ├── ScheduleConfigForm.tsx       ← Posts count, interval, start date, time
    ├── BatchGenerationLoader.tsx    ← "Generating 5 posts..." progress
    ├── ContentCalendar.tsx          ← Main calendar view
    ├── ScheduledPostCard.tsx        ← Individual post card with actions
    └── RescheduleModal.tsx          ← Datetime picker modal
```

---

## Main Page (`src/app/dashboard/schedule/page.tsx`)
```tsx
'use client';
import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import ScheduleStepIndicator from './components/ScheduleStepIndicator';
import ProjectSelector from './components/ProjectSelector';
import ContentStrategyForm from './components/ContentStrategyForm';
import ScheduleConfigForm from './components/ScheduleConfigForm';
import BatchGenerationLoader from './components/BatchGenerationLoader';
import ContentCalendar from './components/ContentCalendar';
import { useGenerationJob } from '@/hooks/useGenerationJob';
import { useToast } from '@/components/ui/use-toast';
import api from '@/lib/api';

type ScheduleStep = 'project' | 'strategy' | 'schedule' | 'generating' | 'calendar';

export default function SchedulePage() {
  const searchParams = useSearchParams();
  const { toast } = useToast();

  const [step, setStep] = useState<ScheduleStep>('project');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(
    searchParams.get('projectId') || null
  );
  const [strategy, setStrategy] = useState({
    tone: 'professional',
    target_audience: 'recruiters',
  });
  const [scheduleConfig, setScheduleConfig] = useState({
    post_count: 5,
    interval_hours: 48,
    start_date: '',
  });
  const [jobId, setJobId] = useState<string | null>(null);
  const [refreshCalendar, setRefreshCalendar] = useState(0);

  // If projectId passed from Instant mode, skip project selection
  useEffect(() => {
    if (selectedProjectId && step === 'project') {
      setStep('strategy');
    }
  }, [selectedProjectId]);

  const { job } = useGenerationJob(step === 'generating' ? jobId : null);

  useEffect(() => {
    if (!job) return;
    if (job.status === 'completed') {
      setStep('calendar');
      setRefreshCalendar(r => r + 1);
      toast({ title: `🗓️ ${job.post_count || scheduleConfig.post_count} posts scheduled!` });
    } else if (job.status === 'failed') {
      toast({ title: 'Generation failed', description: job.message, variant: 'destructive' });
      setStep('schedule');
    }
  }, [job]);

  const handleStartGeneration = async () => {
    if (!selectedProjectId || !scheduleConfig.start_date) return;
    try {
      const res = await api.post('/generate/schedule', {
        project_id: selectedProjectId,
        post_count: scheduleConfig.post_count,
        interval_hours: scheduleConfig.interval_hours,
        start_date: new Date(scheduleConfig.start_date).toISOString(),
        tone: strategy.tone,
        target_audience: strategy.target_audience,
        platform: 'linkedin',
      });
      setJobId(res.data.job_id);
      setStep('generating');
    } catch (err: any) {
      toast({
        title: 'Error',
        description: err.response?.data?.message || 'Failed to start generation.',
        variant: 'destructive',
      });
    }
  };

  const isCreatingNew = step === 'project' || step === 'strategy' || step === 'schedule' || step === 'generating';

  return (
    <div className="max-w-3xl mx-auto py-4">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Growth Automation</h1>
          <p className="text-muted-foreground text-sm">
            Generate and schedule a week of LinkedIn content automatically.
          </p>
        </div>
        {step === 'calendar' && (
          <button
            onClick={() => { setStep('project'); setSelectedProjectId(null); setJobId(null); }}
            className="text-sm text-primary underline"
          >
            + New Schedule
          </button>
        )}
      </div>

      {isCreatingNew && (
        <ScheduleStepIndicator current={step} />
      )}

      <div className="mt-8">
        {step === 'project' && (
          <ProjectSelector
            selectedId={selectedProjectId}
            onSelect={(id) => { setSelectedProjectId(id); setStep('strategy'); }}
          />
        )}
        {step === 'strategy' && (
          <ContentStrategyForm
            values={strategy}
            onChange={setStrategy}
            onBack={() => setStep('project')}
            onNext={() => setStep('schedule')}
          />
        )}
        {step === 'schedule' && (
          <ScheduleConfigForm
            values={scheduleConfig}
            onChange={setScheduleConfig}
            onBack={() => setStep('strategy')}
            onSubmit={handleStartGeneration}
          />
        )}
        {step === 'generating' && (
          <BatchGenerationLoader
            postCount={scheduleConfig.post_count}
            job={job}
          />
        )}
        {step === 'calendar' && (
          <ContentCalendar key={refreshCalendar} />
        )}
      </div>
    </div>
  );
}
```

---

## Schedule Step Indicator (`./components/ScheduleStepIndicator.tsx`)
```tsx
const STEPS = [
  { id: 'project', label: 'Project' },
  { id: 'strategy', label: 'Strategy' },
  { id: 'schedule', label: 'Schedule' },
  { id: 'generating', label: 'Generating' },
];
// Same pattern as StepIndicator from Phase 09 — just different steps
export default function ScheduleStepIndicator({ current }: { current: string }) {
  // Use the same StepIndicator component pattern from Phase 09, pass STEPS above
  return null; // implement using Phase 09 StepIndicator pattern
}
```

---

## Project Selector (`./components/ProjectSelector.tsx`)
```tsx
'use client';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { getProjects } from '@/lib/projects-api';
import { FolderGit2, Plus } from 'lucide-react';
import Link from 'next/link';

export default function ProjectSelector({ selectedId, onSelect }: {
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProjects().then(data => { setProjects(data.items); setLoading(false); });
  }, []);

  if (loading) return <div className="text-muted-foreground text-sm">Loading projects...</div>;

  if (projects.length === 0) {
    return (
      <div className="text-center py-16 space-y-4">
        <FolderGit2 className="w-12 h-12 mx-auto text-muted-foreground/40" />
        <p className="text-muted-foreground">No projects yet.</p>
        <Link href="/dashboard/instant">
          <Button className="gap-2"><Plus className="w-4 h-4" />Create your first project</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Select a project</h2>
      <p className="text-muted-foreground text-sm">Choose a project to generate content from.</p>
      <div className="space-y-3">
        {projects.map(project => (
          <button
            key={project.id}
            onClick={() => onSelect(project.id)}
            className={`w-full text-left border-2 rounded-xl p-4 transition-all hover:border-primary/40 ${
              selectedId === project.id ? 'border-primary bg-primary/5' : 'border-border'
            }`}
          >
            <div className="font-semibold">{project.title}</div>
            <div className="text-sm text-muted-foreground mt-1 line-clamp-1">{project.problem_solved}</div>
            <div className="flex gap-2 mt-2 flex-wrap">
              {project.tech_stack?.slice(0, 3).map((t: string) => (
                <span key={t} className="text-xs bg-muted px-2 py-0.5 rounded-full">{t}</span>
              ))}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
```

---

## Content Strategy Form (`./components/ContentStrategyForm.tsx`)
```tsx
'use client';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export default function ContentStrategyForm({ values, onChange, onBack, onNext }: any) {
  const update = (key: string) => (v: string) => onChange((p: any) => ({ ...p, [key]: v }));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold mb-1">Define your content strategy</h2>
        <p className="text-muted-foreground text-sm">This shapes how the AI writes your posts.</p>
      </div>

      <div className="grid grid-cols-1 gap-4">
        <div>
          <Label>Target Audience</Label>
          <Select defaultValue={values.target_audience} onValueChange={update('target_audience')}>
            <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
            <SelectContent>
              {[
                ['recruiters', 'Recruiters'],
                ['developers', 'Developers'],
                ['students', 'Students'],
                ['startup_founders', 'Startup Founders'],
              ].map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label>Writing Tone</Label>
          <Select defaultValue={values.tone} onValueChange={update('tone')}>
            <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
            <SelectContent>
              {['professional', 'casual', 'storytelling', 'technical', 'inspiring'].map(t => (
                <SelectItem key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack}>Back</Button>
        <Button onClick={onNext} className="flex-1">Continue →</Button>
      </div>
    </div>
  );
}
```

---

## Schedule Config Form (`./components/ScheduleConfigForm.tsx`)
```tsx
'use client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Calendar, Clock } from 'lucide-react';

export default function ScheduleConfigForm({ values, onChange, onBack, onSubmit }: any) {
  const update = (key: string) => (v: any) => onChange((p: any) => ({ ...p, [key]: v }));

  const isValid = values.start_date && values.post_count > 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold mb-1">Configure your schedule</h2>
        <p className="text-muted-foreground text-sm">We'll generate and auto-schedule everything for you.</p>
      </div>

      <div className="space-y-4">
        <div>
          <Label>Number of Posts</Label>
          <Select
            defaultValue={String(values.post_count)}
            onValueChange={v => update('post_count')(Number(v))}
          >
            <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
            <SelectContent>
              {[3, 5, 7, 10, 14].map(n => (
                <SelectItem key={n} value={String(n)}>{n} posts</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label>Post Frequency</Label>
          <Select
            defaultValue={String(values.interval_hours)}
            onValueChange={v => update('interval_hours')(Number(v))}
          >
            <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="24">Daily (every 24h)</SelectItem>
              <SelectItem value="48">Every 2 days</SelectItem>
              <SelectItem value="72">Every 3 days</SelectItem>
              <SelectItem value="168">Weekly</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label>Start Date & Time</Label>
          <Input
            type="datetime-local"
            value={values.start_date}
            onChange={e => update('start_date')(e.target.value)}
            className="mt-1.5"
            min={new Date().toISOString().slice(0, 16)}
          />
        </div>

        {/* Summary Preview */}
        {isValid && (
          <div className="bg-primary/5 border border-primary/20 rounded-xl p-4 text-sm space-y-1">
            <p className="font-medium">Schedule preview:</p>
            {Array.from({ length: Math.min(values.post_count, 3) }).map((_, i) => {
              const d = new Date(values.start_date);
              d.setHours(d.getHours() + values.interval_hours * i);
              return (
                <p key={i} className="text-muted-foreground flex items-center gap-2">
                  <Calendar className="w-3 h-3" />
                  Post {i + 1}: {d.toLocaleString()}
                </p>
              );
            })}
            {values.post_count > 3 && (
              <p className="text-muted-foreground text-xs">+{values.post_count - 3} more posts...</p>
            )}
          </div>
        )}
      </div>

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack}>Back</Button>
        <Button onClick={onSubmit} disabled={!isValid} className="flex-1">
          Generate {values.post_count} Posts
        </Button>
      </div>
    </div>
  );
}
```

---

## Batch Generation Loader (`./components/BatchGenerationLoader.tsx`)
```tsx
'use client';
import { Loader2, CheckCircle } from 'lucide-react';

export default function BatchGenerationLoader({ postCount, job }: { postCount: number; job: any }) {
  const completed = job?.generated_post_ids?.length || 0;

  return (
    <div className="flex flex-col items-center py-16 space-y-8 text-center">
      <Loader2 className="w-16 h-16 text-primary animate-spin" />
      <div>
        <h3 className="text-xl font-semibold">
          Generating {postCount} posts for your content calendar...
        </h3>
        <p className="text-muted-foreground mt-2">
          Each post uses a different content angle. This takes ~{postCount * 20} seconds.
        </p>
      </div>
      {completed > 0 && (
        <div className="flex items-center gap-2 text-green-600 text-sm">
          <CheckCircle className="w-4 h-4" />
          {completed} of {postCount} posts generated
        </div>
      )}
      <div className="flex gap-1.5">
        {Array.from({ length: postCount }).map((_, i) => (
          <div key={i} className={`w-2.5 h-2.5 rounded-full transition-colors ${
            i < completed ? 'bg-green-500' : 'bg-muted'
          }`} />
        ))}
      </div>
    </div>
  );
}
```

---

## Content Calendar (`./components/ContentCalendar.tsx`)
```tsx
'use client';
import { useEffect, useState } from 'react';
import api from '@/lib/api';
import ScheduledPostCard from './ScheduledPostCard';
import { Calendar } from 'lucide-react';

export default function ContentCalendar() {
  const [posts, setPosts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPosts = async () => {
    try {
      const res = await api.get('/schedule?limit=50');
      setPosts(res.data.items);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchPosts(); }, []);

  if (loading) return <div className="text-muted-foreground text-sm">Loading calendar...</div>;

  if (posts.length === 0) {
    return (
      <div className="text-center py-16 space-y-4">
        <Calendar className="w-12 h-12 mx-auto text-muted-foreground/40" />
        <p className="text-muted-foreground">No scheduled posts yet.</p>
        <p className="text-sm text-muted-foreground">Use Growth Automation to schedule your first content series.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">Upcoming Posts ({posts.length})</h2>
      </div>
      <div className="space-y-3">
        {posts.map(post => (
          <ScheduledPostCard key={post.id} post={post} onUpdate={fetchPosts} />
        ))}
      </div>
    </div>
  );
}
```

---

## Scheduled Post Card (`./components/ScheduledPostCard.tsx`)
```tsx
'use client';
import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, Trash2, Eye, Send } from 'lucide-react';
import api from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';

const STATUS_COLORS: Record<string, string> = {
  scheduled: 'default',
  posted: 'secondary',
  failed: 'destructive',
  publishing: 'outline',
};

export default function ScheduledPostCard({ post, onUpdate }: { post: any; onUpdate: () => void }) {
  const { toast } = useToast();
  const [expanded, setExpanded] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [publishing, setPublishing] = useState(false);

  const handleCancel = async () => {
    if (!confirm('Cancel this scheduled post?')) return;
    setCancelling(true);
    try {
      await api.delete(`/schedule/${post.id}`);
      toast({ title: 'Post cancelled.' });
      onUpdate();
    } catch {
      toast({ title: 'Failed to cancel.', variant: 'destructive' });
    } finally {
      setCancelling(false);
    }
  };

  const handlePublishNow = async () => {
    setPublishing(true);
    try {
      await api.post(`/publish/${post.id}`);
      toast({ title: '🎉 Published to LinkedIn!' });
      onUpdate();
    } catch (err: any) {
      toast({ title: 'Publish failed', description: err.response?.data?.message, variant: 'destructive' });
    } finally {
      setPublishing(false);
    }
  };

  const scheduledDate = new Date(post.scheduled_time);

  return (
    <div className="border rounded-xl p-4 bg-card space-y-3 hover:border-primary/30 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Calendar className="w-4 h-4" />
          <span>{scheduledDate.toLocaleDateString()} at {scheduledDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
        <Badge variant={STATUS_COLORS[post.status] as any}>{post.status}</Badge>
      </div>

      <p className={`text-sm leading-relaxed ${expanded ? '' : 'line-clamp-2'}`}>
        {post.content}
      </p>

      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setExpanded(v => !v)}
          className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          <Eye className="w-3 h-3" />
          {expanded ? 'Show less' : 'Show full post'}
        </button>
        <span className="text-muted-foreground/30">·</span>
        <span className="text-xs text-muted-foreground">Angle: {post.angle?.replace('_', ' ')}</span>

        {post.status === 'scheduled' && (
          <>
            <Button size="sm" variant="outline" onClick={handlePublishNow} disabled={publishing} className="ml-auto gap-1.5 h-7">
              <Send className="w-3 h-3" />
              {publishing ? 'Publishing...' : 'Post Now'}
            </Button>
            <Button size="sm" variant="ghost" onClick={handleCancel} disabled={cancelling} className="h-7 text-destructive hover:text-destructive">
              <Trash2 className="w-3 h-3" />
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
```

---

## Implementation Steps (Exact Order)

1. Create all component files under `src/app/dashboard/schedule/`
2. Start with `ProjectSelector` — test it lists projects from API
3. Build `ContentStrategyForm` — pure UI, no API
4. Build `ScheduleConfigForm` with schedule preview
5. Build `BatchGenerationLoader`
6. Build `ScheduledPostCard` with cancel + publish now
7. Build `ContentCalendar` that fetches `/schedule`
8. Wire everything in `page.tsx` state machine
9. Test: select project → configure → generate → calendar shows posts
10. Test: cancel post → removed from calendar
11. Test: "Post Now" on scheduled post → publishes immediately
12. Commit: `git commit -m "Phase 10: Growth Automation & Content Calendar UI"`

---

## Deliverables / Checklist

- [ ] `/dashboard/schedule` page renders
- [ ] Step 1 (Project Selector): lists user projects, click to select
- [ ] Step 2 (Content Strategy): tone + audience dropdowns
- [ ] Step 3 (Schedule Config): count, interval, start date, preview shown
- [ ] Batch generation starts → loader shows progress dots
- [ ] After completion: Content Calendar renders with scheduled posts
- [ ] Each scheduled post card: date, content preview, status badge
- [ ] "Post Now" button publishes immediately
- [ ] Cancel button removes post from calendar
- [ ] "Show full post" expand/collapse works
- [ ] "New Schedule" link resets the flow

---

## Definition of Completion
A user can select a project, configure a 5-post schedule at 2-day intervals, trigger generation, and see all 5 posts appear in the Content Calendar with correct scheduled times. They can cancel any post or publish it early with "Post Now."