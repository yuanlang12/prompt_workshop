import React, { useState, useEffect } from 'react';

const morphTime = 1.5;
const cooldownTime = 0.5;

const useMorphingText = (texts) => {
  const textIndexRef = React.useRef(0);
  const morphRef = React.useRef(0);
  const cooldownRef = React.useRef(0);
  const timeRef = React.useRef(new Date());

  const text1Ref = React.useRef(null);
  const text2Ref = React.useRef(null);

  const setStyles = React.useCallback(
    (fraction) => {
      const [current1, current2] = [text1Ref.current, text2Ref.current];
      if (!current1 || !current2) return;

      current2.style.filter = `blur(${Math.min(8 / fraction - 8, 100)}px)`;
      current2.style.opacity = `${Math.pow(fraction, 0.4) * 100}%`;

      const invertedFraction = 1 - fraction;
      current1.style.filter = `blur(${Math.min(8 / invertedFraction - 8, 100)}px)`;
      current1.style.opacity = `${Math.pow(invertedFraction, 0.4) * 100}%`;

      current1.textContent = texts[textIndexRef.current % texts.length];
      current2.textContent = texts[(textIndexRef.current + 1) % texts.length];
    },
    [texts],
  );

  const doMorph = React.useCallback(() => {
    morphRef.current -= cooldownRef.current;
    cooldownRef.current = 0;

    let fraction = morphRef.current / morphTime;

    if (fraction > 1) {
      cooldownRef.current = cooldownTime;
      fraction = 1;
    }

    setStyles(fraction);

    if (fraction === 1) {
      textIndexRef.current++;
    }
  }, [setStyles]);

  const doCooldown = React.useCallback(() => {
    morphRef.current = 0;
    const [current1, current2] = [text1Ref.current, text2Ref.current];
    if (current1 && current2) {
      current2.style.filter = "none";
      current2.style.opacity = "100%";
      current1.style.filter = "none";
      current1.style.opacity = "0%";
    }
  }, []);

  React.useEffect(() => {
    let animationFrameId;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      const newTime = new Date();
      const dt = (newTime.getTime() - timeRef.current.getTime()) / 1000;
      timeRef.current = newTime;

      cooldownRef.current -= dt;

      if (cooldownRef.current <= 0) doMorph();
      else doCooldown();
    };

    animate();
    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [doMorph, doCooldown]);

  return { text1Ref, text2Ref };
};

const Texts = ({ texts }) => {
  const { text1Ref, text2Ref } = useMorphingText(texts);
  return React.createElement(
    React.Fragment,
    null,
    React.createElement('span', {
      className: 'absolute inset-x-0 top-0 m-auto inline-block w-full',
      ref: text1Ref
    }),
    React.createElement('span', {
      className: 'absolute inset-x-0 top-0 m-auto inline-block w-full',
      ref: text2Ref
    })
  );
};

const SvgFilters = () => React.createElement(
  'svg',
  {
    id: 'filters',
    className: 'hidden',
    preserveAspectRatio: 'xMidYMid slice'
  },
  React.createElement(
    'defs',
    null,
    React.createElement(
      'filter',
      { id: 'threshold' },
      React.createElement('feColorMatrix', {
        in: 'SourceGraphic',
        type: 'matrix',
        values: '1 0 0 0 0\n0 1 0 0 0\n0 0 1 0 0\n0 0 0 255 -140'
      })
    )
  )
);

const MorphingText = ({ texts, className = '' }) => React.createElement(
  'div',
  {
    className: `relative mx-auto h-8 w-full text-center font-sans text-xl font-bold leading-none [filter:url(#threshold)_blur(0.6px)] ${className}`
  },
  React.createElement(Texts, { texts }),
  React.createElement(SvgFilters)
);

export default MorphingText; 