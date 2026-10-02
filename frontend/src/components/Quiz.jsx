import React, { useMemo, useState } from 'react';
import { Check, X, RotateCcw, Award } from 'lucide-react';
import { useSite } from '../context/SiteContext';

export default function Quiz() {
  const { site } = useSite();
  const q = site.quiz || {};
  const questions = useMemo(() => (Array.isArray(q.questions) ? q.questions : []), [q.questions]);

  const [current, setCurrent] = useState(0);
  const [selected, setSelected] = useState(null);
  const [score, setScore] = useState(0);
  const [done, setDone] = useState(false);

  if (!questions.length) return null;

  const total = questions.length;
  const question = questions[current];
  const answered = selected !== null;
  const isCorrect = answered && selected === question.answer;
  const progress = Math.round(((done ? total : current) / total) * 100);

  const pick = (i) => {
    if (answered) return;
    setSelected(i);
    if (i === question.answer) setScore((s) => s + 1);
  };

  const next = () => {
    if (current + 1 >= total) {
      setDone(true);
    } else {
      setCurrent((c) => c + 1);
      setSelected(null);
    }
  };

  const restart = () => {
    setCurrent(0);
    setSelected(null);
    setScore(0);
    setDone(false);
  };

  const pct = Math.round((score / total) * 100);
  const resultMsg =
    pct >= 80 ? 'Beautifully done \u2014 you truly know your stones.' :
    pct >= 50 ? 'A lovely start. A little more and you\u2019ll be a stone whisperer.' :
    'Every journey begins with a single stone. Try again and learn a little more.';

  return (
    <section id="quiz" data-testid="quiz-section" className="py-24 md:py-32 bg-[#f1e7d6]">
      <div className="max-w-2xl mx-auto px-6 md:px-10">
        <div className="text-center mb-10">
          {q.kicker && <p data-testid="quiz-kicker" className="text-xs tracking-[0.3em] uppercase text-[#6b4f3a] mb-4">{q.kicker}</p>}
          {q.title && <h2 data-testid="quiz-title" className="font-serif text-4xl md:text-5xl text-[#1a1410] mb-4 leading-tight">{q.title}</h2>}
          {q.subtitle && <p className="text-[#5a4a3d] leading-relaxed">{q.subtitle}</p>}
        </div>

        <div className="bg-[#faf6f0] rounded-3xl border border-[#e2d5c0] shadow-xl p-7 md:p-10">
          {/* progress */}
          <div className="h-2 rounded-full bg-[#e8dfd1] overflow-hidden mb-8">
            <div className="h-full rounded-full bg-gradient-to-r from-[#a8473d] to-[#c9a876] transition-all duration-500" style={{ width: `${progress}%` }} data-testid="quiz-progress" />
          </div>

          {!done ? (
            <div data-testid="quiz-question-screen">
              <div className="flex items-center justify-between mb-4">
                <span className="inline-block text-xs font-bold tracking-wide uppercase px-3 py-1 rounded-full text-[#faf6f0]" style={{ backgroundColor: question.color || '#6b4f3a' }} data-testid="quiz-gem-badge">{question.gem}</span>
                <span className="text-xs text-[#8b6b4f]">Question {current + 1} of {total}</span>
              </div>

              <h3 className="font-serif text-2xl text-[#1a1410] leading-snug mb-6" data-testid="quiz-question-text">{question.q}</h3>

              <div className="flex flex-col gap-3">
                {(question.options || []).map((opt, i) => {
                  let cls = 'border-[#e2d5c0] bg-[#faf6f0] hover:border-[#c9a876] hover:bg-[#f6efe2]';
                  let icon = null;
                  if (answered) {
                    if (i === question.answer) { cls = 'border-[#5e7a4a] bg-[#eaf0e3] text-[#3c5230]'; icon = <Check className="w-4 h-4 shrink-0" />; }
                    else if (i === selected) { cls = 'border-[#a8473d] bg-[#f6e3df] text-[#8a3328]'; icon = <X className="w-4 h-4 shrink-0" />; }
                    else { cls = 'border-[#e2d5c0] bg-[#faf6f0] opacity-60'; }
                  }
                  return (
                    <button
                      key={i}
                      onClick={() => pick(i)}
                      disabled={answered}
                      data-testid={`quiz-option-${i}`}
                      className={`text-left flex items-center justify-between gap-3 px-5 py-3.5 rounded-2xl border text-[#2c2420] text-sm md:text-base transition-all duration-200 ${cls} ${!answered ? 'hover:translate-x-1' : ''}`}
                    >
                      <span>{opt}</span>
                      {icon}
                    </button>
                  );
                })}
              </div>

              {answered && (
                <div data-testid="quiz-feedback" className={`mt-5 p-4 rounded-2xl text-sm leading-relaxed border ${isCorrect ? 'bg-[#eaf0e3] border-[#c3d3b2] text-[#3c5230]' : 'bg-[#f6e3df] border-[#e3c3bc] text-[#8a3328]'}`}>
                  <span className="font-semibold">{isCorrect ? 'Correct. ' : 'Not quite. '}</span>{question.feedback}
                </div>
              )}

              {answered && (
                <button onClick={next} data-testid="quiz-next-btn" className="mt-6 w-full py-3.5 rounded-full bg-[#1a1410] text-[#faf6f0] text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors">
                  {current + 1 >= total ? 'See my result' : 'Next question'}
                </button>
              )}
            </div>
          ) : (
            <div className="text-center py-4" data-testid="quiz-result-screen">
              <div className="w-28 h-28 rounded-full bg-gradient-to-br from-[#6b4f3a] to-[#a8473d] text-[#faf6f0] flex flex-col items-center justify-center mx-auto mb-6 shadow-lg">
                <Award className="w-5 h-5 mb-1 text-[#e9d9bf]" />
                <span className="text-3xl font-serif font-bold" data-testid="quiz-score">{score}/{total}</span>
              </div>
              <h3 className="font-serif text-3xl text-[#1a1410] mb-3">Quiz complete</h3>
              <p className="text-[#5a4a3d] leading-relaxed mb-8 max-w-sm mx-auto">{resultMsg}</p>
              <button onClick={restart} data-testid="quiz-restart-btn" className="inline-flex items-center gap-2 px-7 py-3 rounded-full bg-[#1a1410] text-[#faf6f0] text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors">
                <RotateCcw className="w-4 h-4" /> {q.retryLabel || 'Try Again'}
              </button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
