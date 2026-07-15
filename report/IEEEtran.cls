% IEEEtran-compatible.cls
% A lightweight local substitute that emulates the IEEE conference
% two-column layout (Times fonts, tight margins, author block macros,
% IEEEkeywords environment). Used only because the real IEEEtran.cls
% could not be fetched (no network access in this environment).
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{IEEEtran}[2026/01/01 local IEEE-conference-style substitute]

\newif\if@ieee@conference
\DeclareOption{conference}{\@ieee@conferencetrue}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions\relax

\LoadClass[10pt,twocolumn]{article}

\RequirePackage[T1]{fontenc}
\RequirePackage{times}
\RequirePackage[margin=0.75in,columnsep=0.25in]{geometry}
\RequirePackage{titlesec}
\RequirePackage{authblk}
\RequirePackage{etoolbox}

\setlength{\parindent}{1em}
\renewcommand{\baselinestretch}{0.98}

\titleformat{\section}{\normalfont\large\bfseries}{\Roman{section}.}{0.6em}{}
\titleformat{\subsection}{\normalfont\bfseries}{\Alph{subsection}.}{0.6em}{}
\titlespacing*{\section}{0pt}{2ex plus 1ex minus .2ex}{1ex}
\titlespacing*{\subsection}{0pt}{1.5ex plus 1ex minus .2ex}{0.8ex}

\providecommand{\IEEEoverridecommandlockouts}{}

% ---- title / author block emulation ----
\def\@ieee@authorblocks{}
\newcommand{\IEEEauthorblockN}[1]{{\normalsize\bfseries #1}\\}
\newcommand{\IEEEauthorblockA}[1]{{\small #1}\\[0.6em]}

\renewenvironment{abstract}{%
  \noindent{\bfseries\itshape Abstract---}%
}{%
  \par\vspace{0.6em}%
}

\newenvironment{IEEEkeywords}{%
  \par\noindent{\bfseries\itshape Index Terms---}%
}{%
  \par\vspace{0.6em}%
}

\renewcommand{\maketitle}{%
  \twocolumn[{%
    \centering
    {\LARGE\bfseries \@title \par}
    \vspace{1em}
    {\@author \par}
    \vspace{1em}
  }]%
  \saythanks
}
\def\saythanks{}

% Author list separated by \and, centered, run inline
\def\and{\hfil\break}

\endinput
