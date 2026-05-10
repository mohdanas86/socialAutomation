'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import client from '@/lib/api'

import { Button } from '@/components/ui/button'
import {
    Field,
    FieldDescription,
    FieldGroup,
    FieldLabel,
    FieldSeparator,
    FieldSet,
} from '@/components/ui/field'

import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
} from '@/components/ui/card'

import {
    Select,
    SelectContent,
    SelectGroup,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'

import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

import {
    LightbulbIcon,
    HashIcon,
} from 'lucide-react'

const MAX_CHARS = 1300
const MIN_CHARS = 300

const TIPS = [
    'Use storytelling for better engagement',
    'Posts with hooks perform better',
    'Add CTA to increase comments',
    'Keep posts human and conversational',
    'Educational posts build authority faster',
]

type GeneratePostForm = {
    topic: string
    niche: string

    postCount: number

    targetAudience: string

    tones: string[]

    contentGoal:
    | 'engagement'
    | 'personal_branding'
    | 'education'
    | 'lead_generation'

    postStyle:
    | 'storytelling'
    | 'educational'
    | 'professional'
    | 'viral'
    | 'thought_leadership'

    schedule: {
        preferredTime: 'morning' | 'afternoon' | 'evening'
        gapHours: number
        startDate: string
    }

    aiOptions: {
        includeHook: boolean
        includeCTA: boolean
        includeHashtags: boolean
        includeEmojis: boolean
        humanLike: boolean
        conciseWriting: boolean
    }

    constraints: {
        minChars: number
        maxChars: number
    }

    keywords: string[]

    customInstructions: string
}

const AVAILABLE_TONES = [
    'Professional',
    'Casual',
    'Funny',
    'Inspirational',
    'Educational',
    'Storytelling',
    'Bold',
]

export default function CreatePostPage() {
    const router = useRouter()

    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const [keywordInput, setKeywordInput] = useState('')

    const [formData, setFormData] = useState<GeneratePostForm>({
        topic: '',
        niche: '',

        postCount: 1,

        targetAudience: '',

        tones: ['Professional'],

        contentGoal: 'engagement',

        postStyle: 'professional',

        schedule: {
            preferredTime: 'morning',
            gapHours: 12,
            startDate: '',
        },

        aiOptions: {
            includeHook: true,
            includeCTA: true,
            includeHashtags: true,
            includeEmojis: false,
            humanLike: true,
            conciseWriting: true,
        },

        constraints: {
            minChars: MIN_CHARS,
            maxChars: MAX_CHARS,
        },

        keywords: [],

        customInstructions: '',
    })

    const updateForm = (
        key: keyof GeneratePostForm,
        value: any
    ) => {
        setFormData((prev) => ({
            ...prev,
            [key]: value,
        }))
    }

    const updateSchedule = (
        key: keyof GeneratePostForm['schedule'],
        value: any
    ) => {
        setFormData((prev) => ({
            ...prev,
            schedule: {
                ...prev.schedule,
                [key]: value,
            },
        }))
    }

    const updateAIOptions = (
        key: keyof GeneratePostForm['aiOptions'],
        value: boolean
    ) => {
        setFormData((prev) => ({
            ...prev,
            aiOptions: {
                ...prev.aiOptions,
                [key]: value,
            },
        }))
    }

    const toggleTone = (tone: string) => {
        setFormData((prev) => ({
            ...prev,
            tones: prev.tones.includes(tone)
                ? prev.tones.filter((t) => t !== tone)
                : [...prev.tones, tone],
        }))
    }

    const addKeyword = () => {
        const value = keywordInput.trim()

        if (!value) return

        if (formData.keywords.includes(value)) return

        setFormData((prev) => ({
            ...prev,
            keywords: [...prev.keywords, value],
        }))

        setKeywordInput('')
    }

    const removeKeyword = (keyword: string) => {
        setFormData((prev) => ({
            ...prev,
            keywords: prev.keywords.filter((k) => k !== keyword),
        }))
    }

    const isValid =
        formData.topic.trim().length > 2 &&
        formData.targetAudience.trim().length > 1 &&
        formData.tones.length > 0

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!isValid) return

        setIsLoading(true)
        setError(null)

        try {
            const payload = {
                ...formData,
                generatedAt: new Date().toISOString(),
            }

            console.log('AI Generation Payload:', payload)

            await client.post('/api/posts/generate', payload)

            router.push('/dashboard/posts')
        } catch (err: any) {
            setError(
                err?.message || 'Something went wrong.'
            )
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="px-4 lg:px-6 max-w-full pb-10">
            {/* Header */}
            <div className="mb-6">
                <h2 className="text-2xl font-semibold tracking-tight">
                    AI LinkedIn Post Generator
                </h2>

                <p className="text-sm text-muted-foreground mt-1">
                    Generate high quality AI-powered LinkedIn posts
                </p>
            </div>

            <div className="grid gap-10 lg:grid-cols-[1fr_300px]">
                {/* FORM */}
                <form onSubmit={handleSubmit}>
                    <FieldGroup>
                        <FieldSet className="space-y-8">

                            {/* TOPIC */}
                            <Field>
                                <FieldLabel>
                                    Topic *
                                </FieldLabel>

                                <Input
                                    placeholder="AI Automation"
                                    value={formData.topic}
                                    onChange={(e) =>
                                        updateForm(
                                            'topic',
                                            e.target.value
                                        )
                                    }
                                />

                                <FieldDescription>
                                    Main topic AI should write about
                                </FieldDescription>
                            </Field>

                            {/* NICHE */}
                            <Field>
                                <FieldLabel>
                                    Niche
                                </FieldLabel>

                                <Input
                                    placeholder="SaaS, AI, Startups, Web Development"
                                    value={formData.niche}
                                    onChange={(e) =>
                                        updateForm(
                                            'niche',
                                            e.target.value
                                        )
                                    }
                                />
                            </Field>

                            {/* POST COUNT */}
                            <Field>
                                <FieldLabel>
                                    Post Count *
                                </FieldLabel>

                                <Select
                                    value={String(formData.postCount)}
                                    onValueChange={(value) =>
                                        updateForm(
                                            'postCount',
                                            Number(value)
                                        )
                                    }
                                >
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>

                                    <SelectContent>
                                        <SelectGroup>
                                            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                                                <SelectItem
                                                    key={num}
                                                    value={String(num)}
                                                >
                                                    {num}
                                                </SelectItem>
                                            ))}
                                        </SelectGroup>
                                    </SelectContent>
                                </Select>
                            </Field>

                            {/* AUDIENCE */}
                            <Field>
                                <FieldLabel>
                                    Target Audience *
                                </FieldLabel>

                                <Select
                                    value={formData.targetAudience}
                                    onValueChange={(value) =>
                                        updateForm(
                                            'targetAudience',
                                            value
                                        )
                                    }
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select audience" />
                                    </SelectTrigger>

                                    <SelectContent>
                                        <SelectGroup>
                                            <SelectItem value="Developers">
                                                Developers
                                            </SelectItem>

                                            <SelectItem value="Startup Founders">
                                                Startup Founders
                                            </SelectItem>

                                            <SelectItem value="Students">
                                                Students
                                            </SelectItem>

                                            <SelectItem value="Recruiters">
                                                Recruiters
                                            </SelectItem>

                                            <SelectItem value="Creators">
                                                Creators
                                            </SelectItem>

                                            <SelectItem value="AI Engineers">
                                                AI Engineers
                                            </SelectItem>
                                        </SelectGroup>
                                    </SelectContent>
                                </Select>
                            </Field>

                            {/* TONES */}
                            <Field>
                                <FieldLabel>
                                    Tone *
                                </FieldLabel>

                                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-3">
                                    {AVAILABLE_TONES.map((tone) => (
                                        <div
                                            key={tone}
                                            className="flex items-center gap-2"
                                        >
                                            <Checkbox
                                                checked={formData.tones.includes(tone)}
                                                onCheckedChange={() =>
                                                    toggleTone(tone)
                                                }
                                            />

                                            <span className="text-sm">
                                                {tone}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </Field>

                            {/* CONTENT GOAL */}
                            <Field>
                                <FieldLabel>
                                    Content Goal
                                </FieldLabel>

                                <Select
                                    value={formData.contentGoal}
                                    onValueChange={(value: any) =>
                                        updateForm(
                                            'contentGoal',
                                            value
                                        )
                                    }
                                >
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>

                                    <SelectContent>
                                        <SelectGroup>
                                            <SelectItem value="engagement">
                                                Engagement
                                            </SelectItem>

                                            <SelectItem value="personal_branding">
                                                Personal Branding
                                            </SelectItem>

                                            <SelectItem value="education">
                                                Education
                                            </SelectItem>

                                            <SelectItem value="lead_generation">
                                                Lead Generation
                                            </SelectItem>
                                        </SelectGroup>
                                    </SelectContent>
                                </Select>
                            </Field>

                            {/* POST STYLE */}
                            <Field>
                                <FieldLabel>
                                    Post Style
                                </FieldLabel>

                                <Select
                                    value={formData.postStyle}
                                    onValueChange={(value: any) =>
                                        updateForm(
                                            'postStyle',
                                            value
                                        )
                                    }
                                >
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>

                                    <SelectContent>
                                        <SelectGroup>
                                            <SelectItem value="storytelling">
                                                Storytelling
                                            </SelectItem>

                                            <SelectItem value="educational">
                                                Educational
                                            </SelectItem>

                                            <SelectItem value="professional">
                                                Professional
                                            </SelectItem>

                                            <SelectItem value="viral">
                                                Viral
                                            </SelectItem>

                                            <SelectItem value="thought_leadership">
                                                Thought Leadership
                                            </SelectItem>
                                        </SelectGroup>
                                    </SelectContent>
                                </Select>
                            </Field>

                            {/* SCHEDULE */}
                            <FieldGroup className="grid md:grid-cols-3 gap-4">

                                <Field>
                                    <FieldLabel>
                                        Preferred Time
                                    </FieldLabel>

                                    <Select
                                        value={formData.schedule.preferredTime}
                                        onValueChange={(value: any) =>
                                            updateSchedule(
                                                'preferredTime',
                                                value
                                            )
                                        }
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>

                                        <SelectContent>
                                            <SelectGroup>
                                                <SelectItem value="morning">
                                                    Morning
                                                </SelectItem>

                                                <SelectItem value="afternoon">
                                                    Afternoon
                                                </SelectItem>

                                                <SelectItem value="evening">
                                                    Evening
                                                </SelectItem>
                                            </SelectGroup>
                                        </SelectContent>
                                    </Select>
                                </Field>

                                <Field>
                                    <FieldLabel>
                                        Gap Hours
                                    </FieldLabel>

                                    <Select
                                        value={String(formData.schedule.gapHours)}
                                        onValueChange={(value: any) =>
                                            updateSchedule(
                                                'gapHours',
                                                Number(value)
                                            )
                                        }
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>

                                        <SelectContent>
                                            <SelectGroup>
                                                {[1, 2, 6, 12, 24].map((hours) => (
                                                    <SelectItem
                                                        key={hours}
                                                        value={String(hours)}
                                                    >
                                                        {hours} {hours === 1 ? 'Hour' : 'Hours'}
                                                    </SelectItem>
                                                ))}
                                            </SelectGroup>
                                        </SelectContent>
                                    </Select>
                                </Field>

                                <Field>
                                    <FieldLabel>
                                        Start Date
                                    </FieldLabel>

                                    <Input
                                        type="date"
                                        value={formData.schedule.startDate}
                                        onChange={(e) =>
                                            updateSchedule(
                                                'startDate',
                                                e.target.value
                                            )
                                        }
                                    />
                                </Field>

                            </FieldGroup>

                            {/* AI OPTIONS */}
                            <Field>
                                <FieldLabel>
                                    AI Options
                                </FieldLabel>

                                <div className="grid md:grid-cols-2 gap-4 mt-4">

                                    {[
                                        ['includeHook', 'Include Hook'],
                                        ['includeCTA', 'Include CTA'],
                                        ['includeHashtags', 'Include Hashtags'],
                                        ['includeEmojis', 'Include Emojis'],
                                        ['humanLike', 'Human Written Style'],
                                        ['conciseWriting', 'Concise Writing'],
                                    ].map(([key, label]) => (
                                        <div
                                            key={key}
                                            className="flex items-center gap-2"
                                        >
                                            <Checkbox
                                                checked={
                                                    formData.aiOptions[
                                                    key as keyof typeof formData.aiOptions
                                                    ]
                                                }
                                                onCheckedChange={(checked) =>
                                                    updateAIOptions(
                                                        key as keyof typeof formData.aiOptions,
                                                        !!checked
                                                    )
                                                }
                                            />

                                            <span className="text-sm">
                                                {label}
                                            </span>
                                        </div>
                                    ))}

                                </div>
                            </Field>

                            {/* KEYWORDS */}
                            <Field>
                                <FieldLabel>
                                    Keywords
                                </FieldLabel>

                                <div className="flex gap-2">
                                    <Input
                                        placeholder="AI Agents"
                                        value={keywordInput}
                                        onChange={(e) =>
                                            setKeywordInput(
                                                e.target.value
                                            )
                                        }
                                    />

                                    <Button
                                        type="button"
                                        variant="outline"
                                        onClick={addKeyword}
                                    >
                                        Add
                                    </Button>
                                </div>

                                <div className="flex flex-wrap gap-2 mt-3">
                                    {formData.keywords.map((keyword) => (
                                        <div
                                            key={keyword}
                                            className="px-3 py-1 rounded-full border text-sm flex items-center gap-2"
                                        >
                                            {keyword}

                                            <button
                                                type="button"
                                                onClick={() =>
                                                    removeKeyword(keyword)
                                                }
                                            >
                                                ×
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </Field>

                            {/* CUSTOM INSTRUCTIONS */}
                            <Field>
                                <FieldLabel>
                                    Custom AI Instructions
                                </FieldLabel>

                                <Textarea
                                    rows={6}
                                    placeholder="Write like a startup founder. Avoid robotic language. Make the content authentic and engaging."
                                    value={formData.customInstructions}
                                    onChange={(e) =>
                                        updateForm(
                                            'customInstructions',
                                            e.target.value
                                        )
                                    }
                                />

                                <FieldDescription>
                                    Extra instructions for AI generation
                                </FieldDescription>
                            </Field>

                        </FieldSet>

                        <FieldSeparator />

                        {/* ERROR */}
                        {error && (
                            <div className="text-sm text-red-500">
                                {error}
                            </div>
                        )}

                        {/* BUTTONS */}
                        <div className="flex items-center gap-4">
                            <Button
                                type="submit"
                                disabled={!isValid || isLoading}
                                className="px-6"
                            >
                                {isLoading
                                    ? 'Generating...'
                                    : 'Generate Posts'}
                            </Button>

                            <Button
                                type="button"
                                variant="outline"
                                onClick={() =>
                                    router.push('/dashboard/posts')
                                }
                            >
                                Cancel
                            </Button>
                        </div>
                    </FieldGroup>
                </form>

                {/* SIDEBAR */}
                <div className="space-y-4">

                    <Card className="border-border/40 bg-card/40">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm flex items-center gap-2">
                                <LightbulbIcon className="h-4 w-4 text-amber-400" />
                                AI Writing Tips
                            </CardTitle>
                        </CardHeader>

                        <CardContent className="space-y-2">
                            {TIPS.map((tip, i) => (
                                <div
                                    key={i}
                                    className="flex gap-2 text-xs text-muted-foreground"
                                >
                                    <span className="text-primary">
                                        •
                                    </span>

                                    {tip}
                                </div>
                            ))}
                        </CardContent>
                    </Card>

                    <Card className="border-border/40 bg-card/40">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm flex items-center gap-2">
                                <HashIcon className="h-4 w-4 text-violet-400" />
                                Character Guide
                            </CardTitle>
                        </CardHeader>

                        <CardContent className="space-y-3 text-xs text-muted-foreground">

                            <div className="flex justify-between">
                                <span>Minimum</span>

                                <span className="font-medium">
                                    {MIN_CHARS}
                                </span>
                            </div>

                            <div className="flex justify-between">
                                <span>Best Range</span>

                                <span className="font-medium text-emerald-400">
                                    600–1300
                                </span>
                            </div>

                            <div className="flex justify-between">
                                <span>Maximum</span>

                                <span className="font-medium">
                                    {MAX_CHARS}
                                </span>
                            </div>



                        </CardContent>
                    </Card>

                </div>
            </div>
        </div>
    )
}