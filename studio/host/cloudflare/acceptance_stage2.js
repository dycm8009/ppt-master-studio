export const ACCEPTANCE_STAGE2_SESSION = '82d3c16f96b0dfa30aefcf61333ae271f55943428f7ae374';
export const ACCEPTANCE_STAGE2_HOST_KEY = '2a09646bb23258b6cb542262d8d43808fadf354e11dcc7b0a5ccfc1745470697';

export const ACCEPTANCE_STAGE2_SNAPSHOT = {
  session: {
    phase: 'strategist',
    status: 'active',
    current_stage: 'stage2',
    expected_stage: 'stage2',
    expected_stage_number: 2,
    recommendation_stage: 'stage2',
    recommendation_stage_number: 2,
    result_stage: 'stage1',
    result_stage_number: 1,
  },
  recommendations: {
    stage: 'stage2',
    lang: 'zh',
    primary_language: 'zh-CN',
    recommend: {
      canvas: 'ppt169',
      delivery_purpose: 'balanced',
      generation_mode: 'continuous',
      image_ai_path: 'auto',
      refine_spec: false,
    },
    audience: { value: '研发团队、架构师和性能工程师' },
    communication_intent: { value: '解释系统架构与性能诊断路径，并推动团队形成可执行的工程共识。' },
    audience_outcome: { value: '团队能够理解关键系统边界、性能证据与下一步架构决策。' },
    core_message: { value: '可靠的技术决策必须建立在清晰架构边界、可观测证据和可执行验证路径之上。' },
    delivery_context: { value: '主要用于 20 分钟技术分享；会后作为设计评审和工程复盘材料。' },
    artifact_afterlife: { value: '后续设计评审、问题复盘和工程实施参考。' },
    content_divergence: { value: '' },
    page_count: { value: '16-20' },
    design_directions: {
      selected: 1,
      candidates: [
        {
          id: 'engineering-blueprint',
          name_zh: '工程蓝图',
          name_en: 'Engineering Blueprint',
          note_zh: '强调系统边界、调用关系和工程可执行性，适合架构拆解与技术机制说明。',
          mode: 'pyramid',
          visual_style: 'blueprint',
          color: {
            name_zh: '蓝图工程',
            palette: {
              background: '#F7F9FC',
              secondary_bg: '#E8EEF5',
              primary: '#18324A',
              accent: '#2D7FF9',
              secondary_accent: '#4DB6AC',
              body_text: '#243447'
            }
          },
          typography: {
            name_zh: '工程无衬线',
            heading: { primary: 'DengXian', english: 'Arial', css: 'sans-serif' },
            body: { primary: 'Microsoft YaHei', english: 'Arial', css: 'sans-serif' },
            body_size: '24',
            sizes: { title: '48', subtitle: '32', annotation: '16' }
          },
          icons: 'tabler-outline',
          image_strategy: {
            name_zh: '技术蓝图',
            rendering: 'blueprint',
            visual: '结构化系统图、调用链与模块边界',
            mood: '精确、工程化、可信'
          }
        },
        {
          id: 'dark-tech-diagnostics',
          name_zh: '深色技术诊断',
          name_en: 'Dark Tech Diagnostics',
          note_zh: '高对比深色技术界面，突出架构关系、性能信号、Trace 证据和诊断结论。',
          mode: 'briefing',
          visual_style: 'dark-tech',
          color: {
            name_zh: '深色诊断',
            palette: {
              background: '#0B0D12',
              secondary_bg: '#171B24',
              primary: '#F4F7FB',
              accent: '#E66C63',
              secondary_accent: '#53A7FF',
              body_text: '#C9D2DF'
            }
          },
          typography: {
            name_zh: '深色技术无衬线',
            heading: { primary: 'DengXian', english: 'Arial', css: 'sans-serif' },
            body: { primary: 'Microsoft YaHei', english: 'Arial', css: 'sans-serif' },
            body_size: '24',
            sizes: { title: '48', subtitle: '32', annotation: '16' }
          },
          icons: 'phosphor-duotone',
          image_strategy: {
            name_zh: '数字诊断界面',
            rendering: 'digital-dashboard',
            visual: '系统节点、性能指标、Trace 证据与诊断关系',
            mood: '克制、可信、高信息密度'
          }
        },
        {
          id: 'editorial-evidence',
          name_zh: '编辑式证据',
          name_en: 'Editorial Evidence',
          note_zh: '以证据链和决策叙事组织信息，适合把观点、原因、判断和行动串联起来。',
          mode: 'narrative',
          visual_style: 'data-journalism',
          color: {
            name_zh: '编辑证据',
            palette: {
              background: '#FAF7F1',
              secondary_bg: '#EFE8DC',
              primary: '#222222',
              accent: '#C85C3C',
              secondary_accent: '#8D6E63',
              body_text: '#333333'
            }
          },
          typography: {
            name_zh: '编辑式无衬线',
            heading: { primary: 'Microsoft YaHei', english: 'Arial', css: 'sans-serif' },
            body: { primary: 'Microsoft YaHei', english: 'Arial', css: 'sans-serif' },
            body_size: '24',
            sizes: { title: '46', subtitle: '30', annotation: '16' }
          },
          icons: 'tabler-outline',
          image_strategy: {
            name_zh: '编辑式技术图',
            rendering: 'editorial',
            visual: '真实证据截图、编辑式数据图与技术示意',
            mood: '理性、证据导向、可读'
          }
        }
      ]
    },
    image_usage: { value: ['provided', 'ai'] },
    image_notes: { value: '架构页优先系统图和调用链；性能分析页优先真实 Trace / Perfetto 证据；AI 只用于补充解释抽象机制的技术示意图。' },
    proactive_speaker_notes: { value: true },
    proactive_custom_animations: { value: false },
    proactive_narration_audio: { value: false },
    refine_spec: { value: false }
  }
};
