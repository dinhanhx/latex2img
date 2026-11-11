import {CHARSET, CHARS} from '@mathjax/font-tools/js/CharMap.js';
import {Font, GlyphNames} from '@mathjax/font-tools/js/Font.js';
import {Variants} from '@mathjax/font-tools/js/Variant.js';
import {Delimiters} from '@mathjax/font-tools/js/Delimiters.js';
import {CommonFont, FontDef} from '@mathjax/font-tools/js/CommonFont.js';
import {RANGES} from '@mathjax/font-tools/js/Ranges.js';
import {SVGFont} from '@mathjax/font-tools/js/SVGFont.js';
import {CHTMLFont} from '@mathjax/font-tools/js/CHTMLFont.js';
import {Components} from '@mathjax/font-tools/js/Components.js';


/***********************************************************************************/
/***********************************************************************************/

try {

  //
  // Name-to-Unicode mapping needed for text fonts
  //
  const charNames: GlyphNames = [
    ['uacute', 0xFA], ['ucircumflex', 0xFB], ['udieresis', 0xFC], ['udotbelow', 0x1EE5],
    ['space_uni0309', 0xEA35], ['space_uni030F', 0xEA26], ['space_uni0323', 0xEB19],
    ['space_uni0326', 0xEA1F], ['space_uni0331', 0xEA3E],
    ['copyleft', 0xEB0F], ['died', 0xEB16], ['threequartersemdash', 0xF6DE],
    ['leaf', 0xEB40], ['perthousandzero', 0xEB4D],
    ['Orogate', 0xEC10], ['orogate', 0xEC11],
    ['star', 0x22C6], ['S_S', 0x1E9E], ['f_k', 0xE803],

    ['dotlessiogonek', 0xE000], ['commaaccentcomb', 0xE002],
    ['Aogonekacute', 0xEB03], ['aogonekacute', 0xEB04],
    ['Eogonekacute', 0xEB1E], ['eogonekacute', 0xEB1F],
    ['H_uni0303', 0xEC08], ['h_uni0303', 0xEC09],
    ['Iogonekacute', 0xEB35], ['iogonekacute', 0xEB36],
    ['Jacute', 0xEB3A], ['jacute', 0xEB3B],
    ['J_uni030C', 0xE001],
    ['L_uni0303', 0xEC0A], ['l_uni0303', 0xEC0B],
    ['Oogonekacute', 0xEB48], ['oogonekacute', 0xEB49],
    ['suppress', 0xEB61], ['T_uni0308', 0xEC0E], ['T_uni0303', 0xEC0C], ['t_uni0303', 0xEC0D],
    ['U_uni032F', 0xEB6E], ['u_uni032F', 0xEB6F], ['tieaccentcapital', 0xEB63]
  ];

  const charOptions = {
    charNames,
    ignore: /^\.notdef$|\.(?:sc|sts)$/
  };

  /***********************************************************************************/
  /***********************************************************************************/

  //
  //  Load the Gyre-Pagella fonts
  //
  Font.load({
    'GP-M': ['./fonts/texgyrepagella-math.otf', charOptions],
    'GP-R': ['./fonts/texgyrepagella-regular.otf', charOptions],
    'GP-B': ['./fonts/texgyrepagella-bold.otf', charOptions],
    'GP-I': ['./fonts/texgyrepagella-italic.otf', charOptions],
    'GP-BI': ['./fonts/texgyrepagella-bolditalic.otf', charOptions],
    'CAL-R': ['../subsets/CM-Calligraphic-Regular.otf', {}],
    'CAL-B': ['../subsets/CM-Calligraphic-Bold.otf', {}]
  });

  Font.get('GP-M')
    .addGlyph(Font.buildV('GP-M', [0x23AD, 0x23A7], 0x23B0, 'lmoustache', -500))
    .addGlyph(Font.buildV('GP-M', [0x23A9, 0x23AB], 0x23B1, 'rmoustache', -500))

    .addGlyph(Font.buildH('GP-M', [[0x219A, 'lft'], [0x2190, 'ex'], [0x2190, 'ex']],
                          0x21E0, 'dashleftarrow', [50, 75, 75, 50]))
    .addGlyph(Font.buildH('GP-M', [[0x2190, 'ex'], [0x2190, 'ex'], [0x2192, 'rt']],
                          0x21E2, 'dashrightarrow', [50, 75, 75, 50]))

    .addGlyph(Font.buildV('GP-M', [0x21BE], 0x294C, 'uni294C.tp', 0, 120))
    .addGlyph(Font.buildV('GP-M', [0x21BF], 0x294D, 'uni294D.tp', 0, 0, 120))
    .addGlyph(Font.buildV('GP-M', [0x21C3], 0x294C, 'uni294C.bt', 0, 0, 120))
    .addGlyph(Font.buildV('GP-M', [0x21C2], 0x294D, 'uni294D.bt', 0, 120))

    .addGlyph(Font.buildH('GP-M', [[0x21BC, 'lft'], [0x21C1, 'rt']], 0x294A, 'uni294A'))
    .addGlyph(Font.buildH('GP-M', [[0x21BD, 'lft'], [0x21C0, 'rt']], 0x294B, 'uni294B'))
    .addGlyph(Font.buildV('GP-M', [[0x294C, 'bt' ], [0x294C, 'tp']], 0x294C, 'uni294C', [0, -600]))
    .addGlyph(Font.buildV('GP-M', [[0x294D, 'bt' ], [0x294D, 'tp']], 0x294D, 'uni294D', [0, -600]))
    .addGlyph(Font.buildH('GP-M', [[0x21BC, 'lft'], [0x21C0, 'rt']], 0x294E, 'uni294E'))
    .addGlyph(Font.buildV('GP-M', [[0x294D, 'bt' ], [0x294C, 'tp']], 0x294F, 'uni294F', [0, -600]))
    .addGlyph(Font.buildH('GP-M', [[0x21BD, 'lft'], [0x21C1, 'rt']], 0x2950, 'uni2950'))
    .addGlyph(Font.buildV('GP-M', [[0x294C, 'bt' ], [0x294D, 'tp']], 0x2951, 'uni2951', [0, -600]))
    .addGlyph(Font.buildH('GP-M', [[0x21BC, 'lft'], [0x21A4, 'rt']], 0x295A, 'uni295A'))
    .addGlyph(Font.buildH('GP-M', [[0x21A6, 'lft'], [0x21C0, 'rt']], 0x295B, 'uni295B'))
    .addGlyph(Font.buildV('GP-M', [[0x21A5, 'bt' ], [0x294C, 'tp']], 0x295C, 'uni295C', [-100, -200]))
    .addGlyph(Font.buildV('GP-M', [[0x294D, 'bt' ], [0x21A7, 'tp']], 0x295D, 'uni295D', [0, -500]))
    .addGlyph(Font.buildH('GP-M', [[0x21BD, 'lft'], [0x21A4, 'rt']], 0x295E, 'uni295E'))
    .addGlyph(Font.buildH('GP-M', [[0x21A6, 'lft'], [0x21C1, 'rt']], 0x295F, 'uni295F'))
    .addGlyph(Font.buildV('GP-M', [[0x21A5, 'bt' ], [0x294D, 'tp']], 0x2960, 'uni2960', [-100, -200]))
    .addGlyph(Font.buildV('GP-M', [[0x294C, 'bt' ], [0x21A7, 'tp']], 0x2961, 'uni2961', [0, -500]))
  ;

  /***********************************************************************************/

  //
  //  Operators, arrows, and integrals that should be in largeop
  //
  CHARSET.Ops = CHARS.At(0x2140, 0x2A09).feature('v1').plus(
    CHARS.InRange(0x2190, 0x21FF, 'GP-M', 'v1'),   // arrows
    CHARS.Range(0x220F, 0x2211).feature('v1'),     // operators
    CHARS.Range(0x22C0, 0x22C3).feature('v1'),     // more operators
    CHARS.Range(0x2A00, 0x2A06).feature('v1'),     // more operators
    CHARS.InRange(0x2B00, 0x2B3F, 'GP-M', 'v1'),   // more arrows
  );

  CHARSET.Arrows = CHARS.InRange(0x2190, 0x21FF, 'GP-M', 'h1').plus(
    CHARS.At(0x27A1).feature('h1'),
    CHARS.InRange(0x2B00, 0x2B3F, 'GP-M', 'h1')
  );

  CHARSET.Integrals = CHARS.Range(0x222B, 0x2233).plus(CHARS.At(0x2A0C, 0x2A11));

  //
  //  Accents for use in spacing modifier characters
  //
  CHARSET.SpacingAccents = CHARS.Map({0x2C9: 0xAF, 0x2CA: 0xB4, 0x2CB: 0x60});

  //
  // The MathJax-Pagella variants
  //
  const MathJaxPagellaVariants = Variants.define({
    normal: [
      ['GP-M', [
        CHARS.InRange(0x20, 0x4000, 'GP-M').minus(CHARS.At(
          0x2061       // there is a visible glyph at this location (should be variant form)
        )),
        CHARS.InRange(0xE000, 0xFEFF, 'GP-M'),
        CHARS.InRange(0x1D400, 0x1D7FF, 'GP-M'),
        CHARSET.SpacingAccents
      ]],
      ['GP-R', [
        CHARS.InRange(0x20, 0x4000, 'GP-R').minus(
          CHARS.InRange(0x20, 0x4000, 'GP-M'),
          CHARS.At(0x2061)
        ),
        CHARS.InRange(0xE000, 0xF8FF, 'GP-R').minus(
          CHARS.InRange(0xE000, 0xF8FF, 'GP-M')
        )
      ]]
    ],
    'bold': [
      ['GP-B', [
        CHARS.InRange(0x20, 0x205F, 'GP-B').minus(CHARSET.Alpha, CHARSET.Numbers, CHARSET.Greek, CHARSET.Dotless),
        CHARS.InRange(0x20A0, 0xF8FF, 'GP-B').minus(
          CHARS.At(0x2202, 0x2207, 0x2581, 0x2588, 0x2591, 0x2592, 0x2593)
        ),
        CHARSET.SpacingAccents
      ]],
      ['GP-M', [
        CHARSET.Dotless.feature('mrmb')
      ]]
    ],
    'italic': [
      ['GP-I', [
        CHARS.InRange(0x20, 0x1FFF, 'GP-I').minus(CHARSET.Alpha, CHARSET.Greek, CHARSET.Dotless),
        CHARS.At(0x2020, 0x2021, 0x2030, 0x2031, 0x203D, 0x203F, 0x2040, 0x2052, 0x2054,
                 0x2422, 0x2423, 0x266A, 0x26AD, 0x26AE, 0x2E18, 0x2E40),
        CHARS.InRange(0x20A0, 0x214F, 'GP-I'),
        CHARS.InRange(0xE000, 0xF8FF, 'GP-I'),
        CHARS.Range(0xFB00, 0xFB04),
        CHARSET.SpacingAccents
      ]],
      ['GP-M', [
        CHARS.Map({0x131: 0x1D6A4, 0x237: 0x1D6A5})
      ]]
    ],
    'bold-italic': [
      ['GP-BI', [
        CHARS.InRange(0x20, 0x1FFF, 'GP-BI').minus(CHARSET.Alpha, CHARSET.Greek, CHARSET.Dotless),
        CHARS.At(0x2020, 0x2021, 0x2030, 0x2031, 0x203D, 0x203F, 0x2040, 0x2052, 0x2054,
                 0x2422, 0x2423, 0x266A, 0x26AD, 0x26AE, 0x2E18, 0x2E40),
        CHARS.InRange(0x20A0, 0x214F, 'GP-BI'),
        CHARS.InRange(0xE000, 0xF8FF, 'GP-BI'),
        CHARS.Range(0xFB00, 0xFB04),
        CHARSET.SpacingAccents
      ]],
      ['GP-M', [
        CHARSET.Dotless.feature('mitb')
      ]]
    ],
    'double-struck': ['GP-M', [
      CHARSET.Dotless.feature('ds')
    ]],
    'fraktur': ['GP-M', [
      CHARSET.Dotless.feature('fra')
    ]],
    'bold-fraktur': ['GP-M', [
      CHARSET.Dotless.feature('frab')
    ]],
    'script': ['GP-M', [
      CHARSET.Dotless.feature('cal')
    ]],
    'bold-script': ['GP-M', [
      CHARSET.Dotless.feature('calb')
    ]],
    'sans-serif': ['GP-M', [
      CHARSET.Dotless.feature('ss')
    ]],
    'bold-sans-serif': ['GP-M', [
      CHARSET.Dotless.feature('ssb')
    ]],
    'sans-serif-italic': ['GP-M', [
      CHARSET.Dotless.feature('sso')
    ]],
    'sans-serif-bold-italic': ['GP-M', [
      CHARSET.Dotless.feature('ssbo')
    ]],
    'monospace': ['GP-M', [
      CHARSET.Dotless.feature('tt')
    ]],
    '-smallop': ['GP-M', [
      CHARS.ForFeature('v1', 'GP-M').minus(CHARSET.Ops, CHARSET.Arrows),
      CHARS.ForFeature('h1', 'GP-M').minus(CHARSET.Arrows)
    ]],
    '-largeop': ['GP-M', [
      CHARS.ForFeature('v2', 'GP-M').minus(CHARSET.Integrals),
      CHARSET.Integrals.feature('v3'),
      CHARSET.Ops, CHARSET.Arrows,
      CHARS.ForFeature('h2', 'GP-M')
    ]],
    '-size3': ['GP-M', [
      CHARS.ForFeature('v3', 'GP-M').minus(CHARSET.Integrals),
      CHARSET.Integrals.feature('v2'),
      CHARS.ForFeature('h3', 'GP-M')
    ]],
    '-size4': ['GP-M', [
      CHARS.ForFeature('v4', 'GP-M'),
      CHARS.ForFeature('h4', 'GP-M')
    ]],
    '-size5': ['GP-M', [
      CHARS.ForFeature('v5', 'GP-M'),
      CHARS.ForFeature('h5', 'GP-M')
    ]],
    '-size6': ['GP-M', [
      CHARS.ForFeature('v6', 'GP-M'),
      CHARS.ForFeature('h6', 'GP-M')
    ]],
    '-tex-mathit': ['GP-I', [
      CHARSET.Alpha,
    ]],
    '-tex-calligraphic': ['CAL-R', [
      CHARSET.AlphaUC
    ]],
    '-tex-bold-calligraphic': ['CAL-B', [
      CHARSET.AlphaUC
    ]],
    '-tex-oldstyle': ['GP-R', [
      CHARS.ForFeature('oldstyle', 'GP-R')
    ]],
    '-tex-bold-oldstyle': ['GP-B', [
      CHARS.ForFeature('oldstyle', 'GP-B')
    ]],
    '-tex-variant': [
      ['GP-M', [
        CHARS.At(0x007E).feature('low'),
        CHARS.At(0x2061),
        CHARS.At(0x2014, 0x22C6).feature('alt'),
        CHARS.Range(0x2032, 0x2037).feature('st'),
        CHARS.At(0x2057).feature('st'),
        CHARSET.PseudoScriptsMain,
        CHARSET.PseudoScriptQuotes.feature('st'),
        CHARS.Map({0x2205: 0x2300}),
      ]],
      ['GP-R', [
        CHARS.ForFeature('alt', 'GP-R').minus(CHARS.At(0x2014, 0x22C6)),
        CHARS.ForFeature('mt', 'GP-R').minus(CHARS.At(0x2A))
      ]],
      ['GP-I', [
        CHARS.Map({0x210F: 0x0127})
      ]]
    ],
    '-lf-tp': ['GP-M', [
      CHARS.At(0x20D0, 0x20D6, 0x20ED, 0x20EE,
               0x2190, 0x219A, 0x219E, 0x21A3, 0x21A6, 0x21AA, 0x21AC,
               0x21BC, 0x21BD, 0x21C4, 0x21C6, 0x21C7, 0x21CB, 0x21CC, 0x21CD,
               0x21D0, 0x21DA, 0x21E6, 0x21E8,
               0x2907, 0x2B05, 0x2B31).feature('lft'),
      CHARS.InRange(0x23B4, 0x23E1, 'GP-M', 'lft'),
      CHARS.At(0x2191, 0x219F, 0x21A7, 0x21BE, 0x21BF,
               0x21C5, 0x21C8, 0x21D1, 0x21E7, 0x21E9, 0x21F5,
               0x221A, 0x222B, 0x222C, 0x222D, 0x27E6, 0x27E7, 0x27EE, 0x27EF,
               0x294C, 0x294D, 0x2A0C, 0x2B06).feature('tp')
    ]],
    '-rt-bt': ['GP-M', [
      CHARS.At(0x20D1, 0x20D7, 0x20EC, 0x20EF,
               0x2192, 0x219B, 0x21A0, 0x21A2, 0x21A4, 0x21A9, 0x21AB,
               0x21C0, 0x21C1, 0x21C4, 0x21C6, 0x21C9, 0x21CB, 0x21CC, 0x21CE,
               0x21D2, 0x21DB, 0x21E6, 0x21E8, 0x21F6,
               0x2906, 0x2B0C).feature('rt'),
      CHARS.InRange(0x23B4, 0x23E1, 'GP-M', 'rt'),
      CHARS.At(0x2193, 0x21A1, 0x21A5, 0x21C2, 0x21C3,
               0x21C5, 0x21CA, 0x21D3, 0x21E7, 0x21E9, 0x21F5,
               0x222B, 0x222C, 0x222D,  0x27E6, 0x27E7, 0x27EE, 0x27EF,
               0x294C, 0x294D, 0x2A0C, 0x2B07).feature('bt')
    ]],
    '-ex-md': ['GP-M', [
      CHARS.At(0x007B,
               0x0305, 0x0332, 0x0333, 0x033F, 0x034D, 0x20D0,
               0x2190, 0x2191, 0x21A9, 0x21BC, 0x21BE, 0x21BF,
               0x21C4, 0x21C5, 0x21CB,
               0x21D0, 0x21D1, 0x21DA, 0x21E6, 0x21E7, 0x21F6,
               0x221A, 0x21CE, 0x222C, 0x222D,
               0x23B4, 0x23B5, 0x23DC, 0x23DD, 0x23E0, 0x23E1,
               0x27E6, 0x27E7, 0x27EE, 0x27EF,
               0x2A0C, 0x2B05, 0x2B06).feature('ex'),
      CHARS.At(0x219A, 0x21CD, 0x23DE, 0x23DF).feature('md'),
      CHARS.Map({0x5F: 0x23DF, 0xAF: 0x23DE}).feature('ex')
    ]]
  }, {
    spaces: {
      normal: {0x2061: 0}
    },
    transferHD: [
      [0x2212, 0x002B]    // make minus the same height/depth as plus
    ],
    fixIC: [
      ['-largeop', .125, CHARS.At(0x222B, 0x222C, 0x222D, 0x2A0C)],
      ['-smallop', .11, CHARS.At(0x222B, 0x222C, 0x222D, 0x2A0C)]
    ]
  });

  /***********************************************************************************/
  /***********************************************************************************/

  const MathJaxPagellaDelimiters = Delimiters.define({
    font: 'GP-M',
    variants: MathJaxPagellaVariants,
    sizeVariants: ['normal'],
    stretchVariants: ['normal'],
    readMathTable: true,
    adjustMathTable: {
      0x003D: {parts: [0, [0x003D, ''], 0]},
      0x007C: {parts: [0, [0x2223, ''], 0]},
      0x007D: {parts: [ , 0x007B]},
      0x0305: {parts: [0, , 0]},
      0x0332: {parts: [0, , 0]},
      0x0333: {parts: [0, , 0]},
      0x033F: {parts: [0, , 0]},
      0x034D: {parts: [0x20EE, , 0x20EF]},
      0x2016: {parts: [0, [0x2016, ''], 0]},
      0x20D0: {parts: [ , , 0]},
      0x20D1: {parts: [0, 0x20D0]},
      0x20D6: {parts: [ , 0x20D0, 0]},
      0x20D7: {parts: [0, 0x20D0]},
      0x20E1: {parts: [0x20D6, 0x20D0, 0x20D7]},
      0x20EC: {parts: [0, 0x034D]},
      0x20ED: {parts: [ , 0x034D, 0]},
      0x20EE: {parts: [ , 0x034D, 0]},
      0x20EF: {parts: [0, 0x034D]},
      0x2190: {parts: [ , , 0]},
      0x2191: {parts: [ , , 0]},
      0x2192: {parts: [0, 0x2190]},
      0x2193: {parts: [0, 0x2191]},
      0x2194: {parts: [0x2190, 0x2190, 0x2192]},
      0x2195: {parts: [0x2191, 0x2191, 0x2193]},
      0x219A: {parts: [ , 0x2190, 0]},
      0x219B: {parts: [0, 0x2190, , 0x219A]},
      0x219E: {parts: [ , 0x2190, 0]},
      0x219F: {parts: [ , 0x2191, 0]},
      0x21A0: {parts: [0, 0x2190]},
      0x21A1: {parts: [0, 0x2191]},
      0x21A2: {parts: [0x2190, 0x2190]},
      0x21A3: {parts: [ , 0x2190, 0x2192]},
      0x21A4: {parts: [0x2190, 0x2190]},
      0x21A5: {parts: [0x2191, 0x2191]},
      0x21A6: {parts: [ , 0x2190, 0x2192]},
      0x21A7: {parts: [ , 0x2191, 0x2193]},
      0x21A9: {parts: [0x2190, 0x21A9]},
      0x21AA: {parts: [ , 0x21A9, 0x2192]},
      0x21AB: {parts: [0x2190, 0x21A9]},
      0x21AC: {parts: [ , 0x21A9, 0x2192]},
      0x21AE: {parts: [0x219A, 0x2190, 0x219B, 0x219A]},
      0x21BC: {parts: [ , 0x21BC, 0]},
      0x21BD: {parts: [ , 0x21BC, 0]},
      0x21BE: {parts: [ , , 0]},
      0x21BF: {parts: [ , , 0]},
      0x21C0: {parts: [0, 0x21BC]},
      0x21C1: {parts: [0, 0x21BC]},
      0x21C2: {parts: [0, 0x21BE]},
      0x21C3: {parts: [0, 0x21BF]},
      0x21C6: {parts: [ , 0x21C4]},
      0x21C7: {parts: [ , 0x21C4, 0]},
      0x21C8: {parts: [ , 0x21C5, 0]},
      0x21C9: {parts: [0, 0x21C4]},
      0x21CA: {parts: [0, 0x21C5]},
      0x21CC: {parts: [ , 0x21CB]},
      0x21CD: {parts: [ , 0x21CE, 0]},
      0x21CE: {parts: [0x21D0, , 0x21D2, 0x21CD]},
      0x21CF: {parts: [0, 0x21CE, 0x21D2, 0x21CD]},
      0x21D0: {parts: [ , , 0]},
      0x21D1: {parts: [ , , 0]},
      0x21D2: {parts: [0, 0x21D0]},
      0x21D3: {parts: [0, 0x21D1]},
      0x21D4: {parts: [0x21D0, 0x21D0, 0x21D2]},
      0x21D5: {parts: [0x21D1, 0x21D1, 0x21D3]},
      0x21DA: {parts: [ , , 0]},
      0x21DB: {parts: [0, 0x21DA]},
      0x21E8: {parts: [ , 0x21E6]},
      0x21E9: {parts: [ , 0x21E7]},
      0x21F3: {parts: [0x21E7, 0x21E7, 0x21E9]},
      0x21F5: {parts: [ , 0x21C5]},
      0x21F6: {parts: [0]},
      0x2212: {parts: [0, [0x2212, ''], 0]},
      0x2223: {parts: [0, [0x2223, ''], 0]},
      0x2225: {parts: [0, [0x2225, ''], 0]},
      0x2261: {parts: [0, [0x2261, ''], 0]},
      0x2263: {parts: [0, [0x2263, ''], 0]},
      0x27A1: {parts: [0, 0x2B05, 0x2B0C]},
      0x2906: {parts: [0x21D0, 0x21D0]},
      0x2907: {parts: [, 0x21D0, 0x21D2]},
      0x2B04: {parts: [0x21E6, 0x21E6, 0x21E8]},
      0x2B05: {parts: [ , , 0]},
      0x2B06: {parts: [ , , 0]},
      0x2B07: {parts: [0, 0x2B06]},
      0x2B0C: {parts: [0, 0x2B05]},
      0x2B0D: {parts: [0x2B06, 0x2B06, 0x2B07]},
      0x2B31: {parts: [ , 0x21F6, 0]}
    },
    add: {
      0x2013: {dir: 'H', sizes: 1, parts: [0, 0x2013]},
      0x2014: {dir: 'H', sizes: 1, parts: [0, 0x2014]},
      0x2015: {dir: 'H', parts: [0, 0x2015]},
      0x2017: {dir: 'H', sizes: 1, parts: [0, 0x2017]},
      0x23AA: {dir: 'V', sizes: 1, parts: [0, 0x23AA, 0]},
      0x23B0: {dir: 'V', sizes: 1, parts: [0x23A7, 0x23AA, 0x23AD]},
      0x23B1: {dir: 'V', sizes: 1, parts: [0x23AB, 0x23AA, 0x23A9]},
      0x23D0: {dir: 'V', sizes: 1, parts: [0, 0x2223]},
      0x294A: {dir: 'H', sizes: 1, parts: [[0x21BC, '-lf-tp'], [0x2190, '-ex-md'], [0x21C1, '-rt-bt']]},
      0x294B: {dir: 'H', sizes: 1, parts: [[0x21BD, '-lf-tp'], [0x2190, '-ex-md'], [0x21C0, '-rt-bt']]},
      0x294C: {dir: 'V', sizes: 1, parts: [[0x294C, '-lf-tp'], [0x2191, '-ex-md'], [0x294C, '-rt-bt']]},
      0x294D: {dir: 'V', sizes: 1, parts: [[0x294D, '-lf-tp'], [0x2191, '-ex-md'], [0x294D, '-rt-bt']]},
      0x294E: {dir: 'H', sizes: 1, parts: [[0x21BC, '-lf-tp'], [0x2190, '-ex-md'], [0x21C0, '-rt-bt']]},
      0x294F: {dir: 'V', sizes: 1, parts: [[0x294C, '-lf-tp'], [0x2191, '-ex-md'], [0x294D, '-rt-bt']]},
      0x2950: {dir: 'H', sizes: 1, parts: [[0x21BD, '-lf-tp'], [0x2190, '-ex-md'], [0x21C1, '-rt-bt']]},
      0x2951: {dir: 'V', sizes: 1, parts: [[0x294D, '-lf-tp'], [0x2191, '-ex-md'], [0x294C, '-rt-bt']]},
      0x295A: {dir: 'H', sizes: 1, parts: [[0x21BC, '-lf-tp'], [0x2190, '-ex-md'], [0x21A4, '-rt-bt']]},
      0x295B: {dir: 'H', sizes: 1, parts: [[0x21A6, '-lf-tp'], [0x2190, '-ex-md'], [0x21C0, '-rt-bt']]},
      0x295C: {dir: 'V', sizes: 1, parts: [[0x294C, '-lf-tp'], [0x2191, '-ex-md'], [0x21A5, '-rt-bt']]},
      0x295D: {dir: 'V', sizes: 1, parts: [[0x21A7, '-lf-tp'], [0x2191, '-ex-md'], [0x294D, '-rt-bt']]},
      0x295E: {dir: 'H', sizes: 1, parts: [[0x21BD, '-lf-tp'], [0x2190, '-ex-md'], [0x21A4, '-rt-bt']]},
      0x295F: {dir: 'H', sizes: 1, parts: [[0x21A6, '-lf-tp'], [0x2190, '-ex-md'], [0x21C1, '-rt-bt']]},
      0x2960: {dir: 'V', sizes: 1, parts: [[0x294D, '-lf-tp'], [0x2191, '-ex-md'], [0x21A5, '-rt-bt']]},
      0x2961: {dir: 'V', sizes: 1, parts: [[0x21A7, '-lf-tp'], [0x2191, '-ex-md'], [0x294C, '-rt-bt']]},
    },
    alias: {
      0x002D: 0x2212,
      0x005E: 0x0302,
      0x005F: 0x2013,
      0x007E: 0x0303,
      0x00AF: 0x0305,
      0x02C6: 0x0302,
      0x02C7: 0x030C,
      0x02C9: 0x0305,
      0x02D8: 0x0306,
      0x02DC: 0x0303,
      0x203E: 0x00AF,
      0x2215: 0x002F,
      0x2312: 0x23DC,
      0x2322: 0x23DC,
      0x2323: 0x23DD,
      0x23AF: 0x2013,
      0x2500: 0x2013,
      0x2758: 0x2223,
      0x27F5: 0x2190,
      0x27F6: 0x2192,
      0x27F7: 0x2194,
      0x27F8: 0x21D0,
      0x27F9: 0x21D2,
      0x27FA: 0x21D4,
      0x27FB: 0x21A4,
      0x27FC: 0x21A6,
      0x27FD: 0x2906,
      0x27FE: 0x2907,
      0x3008: 0x27E8,
      0x3009: 0x27E9,
      0xFE37: 0x23DE,
      0xFE38: 0x23DF,
    },
    fullExtenders: {0x221A: [.77, .295 + 1.032]}
  });

  /***********************************************************************************/
  /***********************************************************************************/

  const MathJaxPagellaData: FontDef = {
    name: 'MathJaxPagella',
    prefix: 'GP',
    variants: MathJaxPagellaVariants,
    delimiters: MathJaxPagellaDelimiters,
    variantFallbacks: {
      '-tex-calligraphic': 'script',
      '-tex-bold-calligraphic': 'bold-script'
    },
    remapAccents: {
      0x300: '\u0060',
      0x301: '\u00B4',
      0x304: '\u00AF'
    },
    ranges: [
      ['latin', {LR: {normal: RANGES.LATIN}}],
      ['latin-b', {LB: {bold: RANGES.LATIN}}],
      ['latin-i', {LI: {italic: RANGES.LATIN}}],
      ['latin-bi', {LBI: {'bold-italic': RANGES.LATIN}}],
      ['double-struck', {
        DS: {
          normal: RANGES.DOUBLESTRUCK,
          'double-struck': RANGES.DOTLESS
        }
      }, [
        0x2140
      ]],
      ['fraktur', {
        F: {
          normal: RANGES.FRAKTUR_NORMAL,
          fraktur: RANGES.DOTLESS
        },
        FB: {
          normal: RANGES.FRAKTUR_BOLD,
          'bold-fraktur': RANGES.DOTLESS
        }
      }],
      ['script', {
        S: {
          normal: RANGES.SCRIPT_NORMAL,
          script: RANGES.DOTLESS
        },
        SB: {
          normal: RANGES.SCRIPT_BOLD,
          'bold-script': RANGES.DOTLESS
        }
      }],
      ['sans-serif', {
        SS: {
          normal: RANGES.SANSSERIF_NORMAL,
          'sans-serif': RANGES.DOTLESS
        },
        SSB: {
          normal: RANGES.SANSSERIF_BOLD,
          'bold-sans-serif': RANGES.DOTLESS
        },
        SSI: {
          normal: RANGES.SANSSERIF_ITALIC,
          'sans-serif-italic': RANGES.DOTLESS
        },
        SSBI: {
          normal: RANGES.SANSSERIF_BOLDITALIC,
          'sans-serif-bold-italic': RANGES.DOTLESS
        }
      }],
      ['monospace', {
        M: {
          normal: RANGES.MONOSPACE,
          monospace: RANGES.DOTLESS
        }
      }],
      ['calligraphic', {
        C: {'-tex-calligraphic': RANGES.ALPHAUC},
        CB: {'-tex-bold-calligraphic': RANGES.ALPHAUC}
      }],
      ['symbols', {
        SY: {normal: RANGES.SYMBOLS},
        '': {'-largeop': [0x2140]}
      }, [
        0x2017
      ]],
      ['symbols-b-i', {
        SYB: {bold: RANGES.SYMBOLS},
        SYI: {italic: RANGES.MORE_SYMBOLS},
        SYBI: {'bold-italic': RANGES.MORE_SYMBOLS}
      }],
      ['arrows', {
        AR: {normal: RANGES.ARROWS},
        ARB: {bold: RANGES.ARROWS},
        '': {
          '-largeop': [[0x2190, 0x21FF], 0x27A3, [0x2B00, 0x2B31]],
          '-lf-tp': [[0x21E6, 0x21E9], 0x2907, 0x2B05, 0x2B06],
          '-rt-bt': [[0x21E6, 0x21E9], 0x2906, 0x2B07, 0x2B0C],
          '-ex-md': [0x21E6, 0x21E7, 0x2B05, 0x2B06]
        }
      }, [
        0x219F, [0x2196, 0x2199], 0x21A1, 0x21A5, 0x21A7, 0x21AD, [0x21B0, 0x21B3],
        0x21B6, 0x21B7, [0x21D6, 0x21D9], 0x21DC, 0x21DD, [0x21E6, 0x21E9], 0x21F3,
        0x27A1, 0x27FD, 0x27FE, 0x2906, 0x2907, 0x294C, 0x294D, 0x294F, 0x2951,
        0x295C, 0x295D, 0x2960, 0x2961, [0x2B04, 0x2B07], 0x2B0C, 0x2B0D, 0x2B31
      ]],
      ['accents', {
        AC: {normal: RANGES.ACCENTS},
        '': {
          '-smallop': RANGES.LARGE_ACCENTS,
          '-largeop': RANGES.LARGE_ACCENTS,
          '-size3':   RANGES.LARGE_ACCENTS,
          '-size4':   RANGES.LARGE_ACCENTS,
          '-size5':   RANGES.LARGE_ACCENTS,
          '-size6':   RANGES.LARGE_ACCENTS,
          '-ex-md':   RANGES.LARGE_ACCENTS
        }
      }, [
        0x311, [0x32C, 0x330], 0x332, 0x333, 0x33F, 0x34D, 0x20E9
      ]],
      ['accents-b-i', {
        ACB: {bold: RANGES.ACCENTS},
        ACI: {italic: RANGES.MORE_ACCENTS},
        ACBI: {'bold-italic': RANGES.MORE_ACCENTS}
      }],
      ['shapes', {
        SH: {normal: RANGES.SHAPES},
        SHB: {bold: RANGES.SHAPES},
        '': {
          italic: [0x266A, 0x26AD, 0x26AE],
          'bold-italic': [0x266A, 0x26AD, 0x26AE]
        }
      }],
      ['stretchy', {
        '': {
          normal: RANGES.PARTS,
          bold: RANGES.PARTS,
          '-size3': RANGES.INTEGRALS,
          '-size4': RANGES.INTEGRALS,
          '-size5': RANGES.INTEGRALS,
          '-size6': RANGES.INTEGRALS,
          '-lf-tp': RANGES.INTEGRALS,
          '-rt-bt': RANGES.INTEGRALS,
          '-ex-md': RANGES.INTEGRALS,
        }
      }, [
        [0x222B, 0x2233], 0x2A0C, 0x2A11,
        0x2140, [0x220F, 0x2211], [0x22A2, 0x22A5], [0x22C0, 0x22C3], [0x2A00, 0x2A06], 0x2A09
      ]],
      ['variants', {
        VX: {'-tex-variant': [[0x20, 0xFF], 0x12A, 0x12B, 0x2014, 0x2016, 0x2044, 0x2061, [0x2070, 0x209F], 0x2E40]}
      }],
      ['PUA', {
        PU: {normal: RANGES.PUA},
        PUB: {bold: RANGES.PUA},
        PUI: {italic: RANGES.PUA},
        PUBI: {'bold-italic': RANGES.PUA}
      }]
    ],
    legal: {
      addCopyright: 'Copyright (c) 2022 MathJax, Inc. (www.mathjax.org)'
    }
  };

  /***********************************************************************************/
  /***********************************************************************************/

  CommonFont.define(MathJaxPagellaData).writeFont();

  Components.define('svg', MathJaxPagellaData).writeFont().writeComponent();
  SVGFont.define(MathJaxPagellaData).writeFont();

  Components.define('chtml', MathJaxPagellaData).writeFont().writeComponent();
  CHTMLFont.define(MathJaxPagellaData).writeFont().makeWoffFonts('GP-M');

} catch(err) {
  console.error(err);
  process.exit(1);
}
