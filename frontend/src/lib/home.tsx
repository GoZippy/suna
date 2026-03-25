import { FirstBentoAnimation } from '@/components/home/first-bento-animation';
import { FourthBentoAnimation } from '@/components/home/fourth-bento-animation';
import { SecondBentoAnimation } from '@/components/home/second-bento-animation';
import { ThirdBentoAnimation } from '@/components/home/third-bento-animation';
import { FlickeringGrid } from '@/components/home/ui/flickering-grid';
import { Globe } from '@/components/home/ui/globe';
import { cn } from '@/lib/utils';
import { motion } from 'motion/react';
import { config } from '@/lib/config';

export const Highlight = ({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) => {
  return (
    <span
      className={cn(
        'p-1 py-0.5 font-medium dark:font-semibold text-secondary',
        className,
      )}
    >
      {children}
    </span>
  );
};

export const BLUR_FADE_DELAY = 0.15;

interface UpgradePlan {
  /** @deprecated */
  hours: string;
  price: string;
  tierId: string;
}

export interface PricingTier {
  name: string;
  price: string;
  yearlyPrice?: string; // Add yearly price support
  description: string;
  buttonText: string;
  buttonColor: string;
  isPopular: boolean;
  /** @deprecated */
  hours: string;
  features: string[];
  tierId: string;
  yearlyTierId?: string; // Add yearly tier ID support
  monthlyCommitmentTierId?: string; // Add monthly commitment with yearly commitment support
  monthlyCommitmentStripePriceId?: string; // For Stripe billing (optional for self-hosted)
  upgradePlans: UpgradePlan[];
  hidden?: boolean; // Optional property to hide plans from display while keeping them in code
  billingPeriod?: 'monthly' | 'yearly'; // Add billing period support
  originalYearlyPrice?: string; // For showing crossed-out price
  discountPercentage?: number; // For showing discount badge
}

export const siteConfig = {
  name: 'Zippy Suna',
  description: 'A fully free and self-hosted fork of the open source Kortix Suna project.',
  cta: 'Start Using',
  url: process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:18884',
  keywords: ['Zippy Suna', 'Self-hosted AI', 'Ollama', 'AI Assistant', 'Open Source', 'Kortix Suna Fork'],
  links: {
    email: 'admin@localhost',
    twitter: 'https://github.com/GoZippy/suna',
    github: 'https://github.com/GoZippy/suna',
    instagram: '#',
  },
  nav: {
    links: [
      { id: 1, name: 'Home', href: '#hero' },
      { id: 2, name: 'Features', href: '#features' },
      { id: 3, name: 'Local Setup', href: '#local-setup' },
      { id: 4, name: 'About', href: '#about' },
    ],
  },
  hero: {
    badgeIcon: (
      <svg
        width="14"
        height="14"
        viewBox="0 0 16 16"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="text-muted-foreground"
      >
        <path
          d="M8 1C8.55228 1 9 1.44772 9 2V3C9 3.55228 8.55228 4 8 4C7.44772 4 7 3.55228 7 3V2C7 1.44772 7.44772 1 8 1Z"
          stroke="currentColor"
          strokeWidth="1.5"
        />
        <path
          d="M8 12C8.55228 12 9 12.4477 9 13V14C9 14.5523 8.55228 15 8 15C7.44772 15 7 14.5523 7 14V13C7 12.4477 7.44772 12 8 12Z"
          stroke="currentColor"
          strokeWidth="1.5"
        />
        <path
          d="M1 8C1 7.44772 1.44772 7 2 7H3C3.55228 7 4 7.44772 4 8C4 8.55228 3.55228 9 3 9H2C1.44772 9 1 8.55228 1 8Z"
          stroke="currentColor"
          strokeWidth="1.5"
        />
        <path
          d="M12 8C12 7.44772 12.4477 7 13 7H14C14.5523 7 15 7.44772 15 8C15 8.55228 14.5523 9 14 9H13C12.4477 9 12 8.55228 12 8Z"
          stroke="currentColor"
          strokeWidth="1.5"
        />
      </svg>
    ),
    badge: 'FORK OF SUNA',
    githubUrl: 'https://github.com/GoZippy/suna',
    title: 'Zippy Suna - Your Personal AI Assistant',
    description:
      'A fully free and self-hosted fork of the open source Kortix Suna project. Run AI models locally with Ollama integration.',
    inputPlaceholder: 'Ask your AI to...',
  },
  cloudPricingItems: [
    {
      name: 'Local',
      price: 'Free',
      description: 'Run everything on your machine',
      buttonText: 'Start Using',
      buttonColor: 'bg-secondary text-white',
      isPopular: true,
      /** @deprecated */
      hours: 'Unlimited',
      features: [
        'Full AI capabilities',
        'Unlimited usage',
        'Complete privacy',
        'Local data storage',
        'Ollama integration',
      ],
      tierId: 'local',
      upgradePlans: [],
    },
  ],
  companyShowcase: {
    companyLogos: [
      {
        id: 1,
        name: 'Zippy Suna',
        logo: (
          <svg
            width="110"
            height="31"
            viewBox="0 0 110 31"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="dark:fill-white fill-black"
          >
            <path d="M20 15.5C20 12.4624 22.4624 10 25.5 10H84.5C87.5376 10 90 12.4624 90 15.5V15.5C90 18.5376 87.5376 21 84.5 21H25.5C22.4624 21 20 18.5376 20 15.5V15.5Z" fill="currentColor"/>
            <text x="55" y="18" textAnchor="middle" fill="white" fontSize="12" fontWeight="bold">ZIPPY SUNA</text>
          </svg>
        ),
      },
    ],
  },
  featureSection: {
    title: 'How Zippy Suna Works',
    description:
      'Discover how your Zippy Suna AI platform transforms your commands into action in three simple steps',
    items: [
      {
        id: 1,
        title: 'Ask Your AI',
        content:
          'Simply type your request or question. Your Zippy Suna AI will understand and process your input.',
        image:
          'https://images.unsplash.com/photo-1720371300677-ba4838fa0678?q=80&w=2070&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D',
      },
      {
        id: 2,
        title: 'Local Processing',
        content:
          'Your AI processes everything locally using Ollama models. No data leaves your machine.',
        image:
          'https://images.unsplash.com/photo-1686170287433-c95faf6d3608?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxmZWF0dXJlZC1waG90b3MtZmVlZHwzfHx8ZW58MHx8fHx8fA%3D%3D',
      },
      {
        id: 3,
        title: 'Get Results',
        content:
          'Receive intelligent responses and assistance while maintaining complete privacy and control.',
        image:
          'https://images.unsplash.com/photo-1720378042271-60aff1e1c538?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxmZWF0dXJlZC1waG90b3MtZmVlZHwxMHx8fGVufDB8fHx8fA%3D%3D',
      },
    ],
  },
  bentoSection: {
    title: 'Empower Your Workflow with Zippy Suna',
    description:
      'Experience the power of AI without compromising your privacy or data security.',
    items: [
      {
        id: 1,
        content: <FirstBentoAnimation />,
        title: 'Complete Privacy',
        description:
          'Your data never leaves your machine. All AI processing happens locally with full control over your information.',
      },
      {
        id: 2,
        content: <SecondBentoAnimation />,
        title: 'Ollama Integration',
        description:
          'Seamlessly integrate with Ollama to run various AI models locally. Choose the model that fits your needs.',
      },
      {
        id: 3,
        content: (
          <ThirdBentoAnimation
            data={[20, 30, 25, 45, 40, 55, 75]}
            toolTipValues={[
              1234, 1678, 2101, 2534, 2967, 3400, 3833, 4266, 4700, 5133,
            ]}
          />
        ),
        title: 'Intelligent Responses',
        description:
          "Get smart, contextual responses from your Zippy Suna AI. No internet required, no external dependencies.",
      },
      {
        id: 4,
        content: <FourthBentoAnimation once={false} />,
        title: 'Full Customization',
        description:
          'Customize your AI experience. As a local platform, you have complete control over functionality and appearance.',
      },
    ],
  },
  benefits: [
    {
      id: 1,
      text: "Run AI models locally with complete privacy and control.",
      image: '/Device-6.png',
    },
    {
      id: 2,
      text: 'No external dependencies or data sharing required.',
      image: '/Device-7.png',
    },
    {
      id: 3,
      text: 'Integrate seamlessly with Ollama for model variety.',
      image: '/Device-8.png',
    },
    {
      id: 4,
      text: 'Fully free and open source fork of Kortix Suna.',
      image: '/Device-1.png',
    },
  ],
  growthSection: {
    title: 'Self-Hosted & Secure',
    description:
      'Where advanced AI meets complete privacy—designed to protect your data while providing powerful capabilities.',
    items: [
      {
        id: 1,
        content: (
          <div
            className="relative flex size-full items-center justify-center overflow-hidden transition-all duration-300 hover:[mask-image:none] hover:[webkit-mask-image:none]"
            style={{
              WebkitMaskImage: `url("data:image/svg+xml,%3Csvg width='265' height='268' viewBox='0 0 265 268' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fillRule='evenodd' clipRule='evenodd' d='M121.384 4.5393C124.406 1.99342 128.319 0.585938 132.374 0.585938C136.429 0.585938 140.342 1.99342 143.365 4.5393C173.074 29.6304 210.174 45.6338 249.754 50.4314C253.64 50.9018 257.221 52.6601 259.855 55.3912C262.489 58.1223 264.005 61.6477 264.13 65.3354C265.616 106.338 254.748 146.9 232.782 182.329C210.816 217.759 178.649 246.61 140.002 265.547C137.645 266.701 135.028 267.301 132.371 267.298C129.715 267.294 127.1 266.686 124.747 265.526C86.0991 246.59 53.9325 217.739 31.9665 182.309C10.0005 146.879 -0.867679 106.317 0.618784 65.3147C0.748654 61.6306 2.26627 58.1102 4.9001 55.3833C7.53394 52.6565 11.1121 50.9012 14.9945 50.4314C54.572 45.6396 91.6716 29.6435 121.384 4.56V4.5393Z' fill='black'/%3E%3C/svg%3E")`,
              maskImage: `url("data:image/svg+xml,%3Csvg width='265' height='268' viewBox='0 0 265 268' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fillRule='evenodd' clipRule='evenodd' d='M121.384 4.5393C124.406 1.99342 128.319 0.585938 132.374 0.585938C136.429 0.585938 140.342 1.99342 143.365 4.5393C173.074 29.6304 210.174 45.6338 249.754 50.4314C253.64 50.9018 257.221 52.6601 259.855 55.3912C262.489 58.1223 264.005 61.6477 264.13 65.3354C265.616 106.338 254.748 146.9 232.782 182.329C210.816 217.759 178.649 246.61 140.002 265.547C137.645 266.701 135.028 267.301 132.371 267.298C129.715 267.294 127.1 266.686 124.747 265.526C86.0991 246.59 53.9325 217.739 31.9665 182.309C10.0005 146.879 -0.867679 106.317 0.618784 65.3147C0.748654 61.6306 2.26627 58.1102 4.9001 55.3833C7.53394 52.6565 11.1121 50.9012 14.9945 50.4314C54.572 45.6396 91.6716 29.6435 121.384 4.56V4.5393Z' fill='black'/%3E%3C/svg%3E")`,
              WebkitMaskSize: 'contain',
              maskSize: 'contain',
              WebkitMaskRepeat: 'no-repeat',
              maskPosition: 'center',
            }}
          >
            <div className="absolute top-[55%] md:top-[58%] left-[55%] md:left-[57%] -translate-x-1/2 -translate-y-1/2  size-full z-10">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="227"
                height="244"
                viewBox="0 0 227 244"
                fill="none"
                className="size-[90%] md:size-[85%] object-contain fill-background"
              >
                <path
                  fillRule="evenodd"
                  clipRule="evenodd"
                  d="M104.06 3.61671C106.656 1.28763 110.017 0 113.5 0C116.983 0 120.344 1.28763 122.94 3.61671C148.459 26.5711 180.325 41.2118 214.322 45.6008C217.66 46.0312 220.736 47.6398 222.999 50.1383C225.262 52.6369 226.563 55.862 226.67 59.2357C227.947 96.7468 218.612 133.854 199.744 166.267C180.877 198.68 153.248 225.074 120.052 242.398C118.028 243.454 115.779 244.003 113.498 244C111.216 243.997 108.969 243.441 106.948 242.379C73.7524 225.055 46.1231 198.661 27.2556 166.248C8.38807 133.835 -0.947042 96.7279 0.329744 59.2168C0.441295 55.8464 1.74484 52.6258 4.00715 50.1311C6.26946 47.6365 9.34293 46.0306 12.6777 45.6008C46.6725 41.2171 78.5389 26.5832 104.06 3.63565V3.61671Z"
                />
              </svg>
            </div>
            <div className="absolute top-[58%] md:top-[60%] left-1/2 -translate-x-1/2 -translate-y-1/2  size-full z-20">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="245"
                height="282"
                viewBox="0 0 245 282"
                className="size-full object-contain fill-accent"
              >
                <g filter="url(#filter0_dddd_2_33)">
                  <path
                    fillRule="evenodd"
                    clipRule="evenodd"
                    d="M113.664 7.33065C116.025 5.21236 119.082 4.04126 122.25 4.04126C125.418 4.04126 128.475 5.21236 130.836 7.33065C154.045 28.2076 183.028 41.5233 213.948 45.5151C216.984 45.9065 219.781 47.3695 221.839 49.6419C223.897 51.9144 225.081 54.8476 225.178 57.916C226.339 92.0322 217.849 125.781 200.689 155.261C183.529 184.74 158.4 208.746 128.209 224.501C126.368 225.462 124.323 225.962 122.248 225.959C120.173 225.956 118.13 225.45 116.291 224.484C86.0997 208.728 60.971 184.723 43.811 155.244C26.6511 125.764 18.1608 92.015 19.322 57.8988C19.4235 54.8334 20.6091 51.9043 22.6666 49.6354C24.7242 47.3665 27.5195 45.906 30.5524 45.5151C61.4706 41.5281 90.4531 28.2186 113.664 7.34787V7.33065Z"
                  />
                </g>
                <defs>
                  <filter
                    id="filter0_dddd_2_33"
                    x="0.217041"
                    y="0.0412598"
                    width="244.066"
                    height="292.917"
                    filterUnits="userSpaceOnUse"
                    colorInterpolationFilters="sRGB"
                  >
                    <feFlood floodOpacity="0" result="BackgroundImageFix" />
                    <feColorMatrix
                      in="SourceAlpha"
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                      result="hardAlpha"
                    />
                    <feOffset dy="3" />
                    <feGaussianBlur stdDeviation="3.5" />
                    <feColorMatrix
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.04 0"
                    />
                    <feBlend
                      mode="normal"
                      in2="BackgroundImageFix"
                      result="effect1_dropShadow_2_33"
                    />
                    <feColorMatrix
                      in="SourceAlpha"
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                      result="hardAlpha"
                    />
                    <feOffset dy="12" />
                    <feGaussianBlur stdDeviation="6" />
                    <feColorMatrix
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.04 0"
                    />
                    <feBlend
                      mode="normal"
                      in2="effect1_dropShadow_2_33"
                      result="effect2_dropShadow_2_33"
                    />
                    <feColorMatrix
                      in="SourceAlpha"
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                      result="hardAlpha"
                    />
                    <feOffset dy="27" />
                    <feGaussianBlur stdDeviation="8" />
                    <feColorMatrix
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.02 0"
                    />
                    <feBlend
                      mode="normal"
                      in2="effect2_dropShadow_2_33"
                      result="effect3_dropShadow_2_33"
                    />
                    <feColorMatrix
                      in="SourceAlpha"
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                      result="hardAlpha"
                    />
                    <feOffset dy="48" />
                    <feGaussianBlur stdDeviation="9.5" />
                    <feColorMatrix
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.01 0"
                    />
                    <feBlend
                      mode="normal"
                      in2="effect3_dropShadow_2_33"
                      result="effect4_dropShadow_2_33"
                    />
                    <feBlend
                      mode="normal"
                      in="SourceGraphic"
                      in2="effect4_dropShadow_2_33"
                      result="shape"
                    />
                  </filter>
                </defs>
              </svg>
            </div>
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-30">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="81"
                height="80"
                viewBox="0 0 81 80"
                className="fill-background"
              >
                <g filter="url(#filter0_iiii_2_34)">
                  <path
                    fillRule="evenodd"
                    clipRule="evenodd"
                    d="M20.5 36V28C20.5 22.6957 22.6071 17.6086 26.3579 13.8579C30.1086 10.1071 35.1957 8 40.5 8C45.8043 8 50.8914 10.1071 54.6421 13.8579C58.3929 17.6086 60.5 22.6957 60.5 28V36C62.6217 36 64.6566 36.8429 66.1569 38.3431C67.6571 39.8434 68.5 41.8783 68.5 44V64C68.5 66.1217 67.6571 68.1566 66.1569 69.6569C64.6566 71.1571 62.6217 72 60.5 72H20.5C18.3783 72 16.3434 71.1571 14.8431 69.6569C13.3429 68.1566 12.5 66.1217 12.5 64V44C12.5 41.8783 13.3429 39.8434 14.8431 38.3431C16.3434 36.8429 18.3783 36 20.5 36ZM52.5 28V36H28.5V28C28.5 24.8174 29.7643 21.7652 32.0147 19.5147C34.2652 17.2643 37.3174 16 40.5 16C43.6826 16 46.7348 17.2643 48.9853 19.5147C51.2357 21.7652 52.5 24.8174 52.5 28Z"
                  />
                </g>
                <defs>
                  <filter
                    id="filter0_iiii_2_34"
                    x="12.5"
                    y="8"
                    width="56"
                    height="70"
                    filterUnits="userSpaceOnUse"
                    colorInterpolationFilters="sRGB"
                  >
                    <feFlood floodOpacity="0" result="BackgroundImageFix" />
                    <feBlend
                      mode="normal"
                      in="SourceGraphic"
                      in2="BackgroundImageFix"
                      result="shape"
                    />
                    <feColorMatrix
                      in="SourceAlpha"
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                      result="hardAlpha"
                    />
                    <feOffset dy="1" />
                    <feGaussianBlur stdDeviation="1" />
                    <feComposite
                      in2="hardAlpha"
                      operator="arithmetic"
                      k2="-1"
                      k3="1"
                    />
                    <feColorMatrix
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.1 0"
                    />
                    <feBlend
                      mode="normal"
                      in2="shape"
                      result="effect1_innerShadow_2_34"
                    />
                    <feColorMatrix
                      in="SourceAlpha"
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                      result="hardAlpha"
                    />
                    <feOffset dy="3" />
                    <feGaussianBlur stdDeviation="1.5" />
                    <feComposite
                      in2="hardAlpha"
                      operator="arithmetic"
                      k2="-1"
                      k3="1"
                    />
                    <feColorMatrix
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.09 0"
                    />
                    <feBlend
                      mode="normal"
                      in2="effect1_innerShadow_2_34"
                      result="effect2_innerShadow_2_34"
                    />
                    <feColorMatrix
                      in="SourceAlpha"
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                      result="hardAlpha"
                    />
                    <feOffset dy="8" />
                    <feGaussianBlur stdDeviation="2.5" />
                    <feComposite
                      in2="hardAlpha"
                      operator="arithmetic"
                      k2="-1"
                      k3="1"
                    />
                    <feColorMatrix
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.05 0"
                    />
                    <feBlend
                      mode="normal"
                      in2="effect2_innerShadow_2_34"
                      result="effect3_innerShadow_2_34"
                    />
                    <feColorMatrix
                      in="SourceAlpha"
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
                      result="hardAlpha"
                    />
                    <feOffset dy="14" />
                    <feGaussianBlur stdDeviation="3" />
                    <feComposite
                      in2="hardAlpha"
                      operator="arithmetic"
                      k2="-1"
                      k3="1"
                    />
                    <feColorMatrix
                      type="matrix"
                      values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.01 0"
                    />
                    <feBlend
                      mode="normal"
                      in2="effect3_innerShadow_2_34"
                      result="effect4_innerShadow_2_34"
                    />
                  </filter>
                </defs>
              </svg>
            </div>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="size-full"
            >
              <FlickeringGrid
                className="size-full"
                gridGap={4}
                squareSize={2}
                maxOpacity={0.5}
              />
            </motion.div>
          </div>
        ),

        title: 'Local Privacy',
        description:
          'Your data never leaves your machine. All AI processing happens locally with complete privacy and control.',
      },
      {
        id: 2,
        content: (
          <div className="relative flex size-full max-w-lg items-center justify-center overflow-hidden [mask-image:linear-gradient(to_top,transparent,black_50%)] -translate-y-20">
            <Globe className="top-28" />
          </div>
        ),

        title: 'Ollama Integration',
        description:
          'Seamlessly integrate with Ollama to run various AI models locally. Choose the model that fits your needs.',
      },
    ],
  },
  quoteSection: {
    quote:
      'Having Zippy Suna run locally on my machine gives me complete control over my data while providing powerful capabilities. No more concerns about privacy or external dependencies.',
    author: {
      name: 'Zippy Suna User',
      role: 'Privacy Advocate',
      image: 'https://randomuser.me/api/portraits/men/91.jpg',
    },
  },
  pricing: {
    title: 'Free & Self-Hosted Forever',
    description:
      'Zippy Suna is completely free and runs entirely on your machine. No hidden fees, no external dependencies.',
    pricingItems: [
      {
        name: 'Zippy Suna',
        href: '#',
        price: 'Free',
        period: 'forever',
        yearlyPrice: 'Free',
        features: [
          'Full AI capabilities',
          'Unlimited usage',
          'Complete privacy',
          'Local data storage',
          'Ollama integration',
          'No external dependencies',
          'Full customization',
          'Community support',
        ],
        description: 'Perfect for privacy-conscious users and developers',
        buttonText: 'Start Using',
        buttonColor: 'bg-secondary text-white',
        isPopular: true,
      },
    ],
  },
  testimonials: [
    {
      id: '1',
      name: 'Privacy User',
      role: 'Data Security Advocate',
      img: 'https://randomuser.me/api/portraits/men/91.jpg',
      description: (
        <p>
          Running Zippy Suna locally gives me complete control over my data.
          <Highlight>
            No more concerns about privacy or external dependencies.
          </Highlight>{' '}
          A game-changer for privacy-conscious users.
        </p>
      ),
    },
    {
      id: '2',
      name: 'Zippy Suna Developer',
      role: 'Software Engineer',
      img: 'https://randomuser.me/api/portraits/women/12.jpg',
      description: (
        <p>
          The Ollama integration makes it easy to run various AI models locally.
          <Highlight>Perfect for development and testing!</Highlight>{' '}
          Highly recommend for developers.
        </p>
      ),
    },
  ],
  faqSection: {
    title: 'Frequently Asked Questions',
    description:
      "Answers to common questions about Zippy Suna. If you have any other questions, please don't hesitate to contact us.",
    faQitems: [
      {
        id: 1,
        question: 'What is Zippy Suna?',
        answer:
          'Zippy Suna is a fully free and self-hosted fork of the open source Kortix Suna project. It runs entirely on your machine, processing AI requests locally without sending data to external servers, ensuring complete privacy and control.',
      },
      {
        id: 2,
        question: 'How does Zippy Suna work?',
        answer:
          'Zippy Suna works by analyzing your requirements and processing them using AI models running locally on your machine. It integrates with Ollama to provide various AI capabilities while maintaining complete privacy.',
      },
      {
        id: 3,
        question: 'Is Zippy Suna really free?',
        answer:
          'Yes, Zippy Suna is completely free and open source. We believe in democratizing AI technology and making it accessible to everyone while maintaining privacy and control.',
      },
      {
        id: 4,
        question: 'Can I integrate with Ollama?',
        answer:
          'Yes, Zippy Suna is designed to seamlessly integrate with Ollama. You can run various AI models locally and choose the one that best fits your needs.',
      },
      {
        id: 5,
        question: 'How can I contribute to Zippy Suna?',
        answer:
          'You can contribute to Zippy Suna by submitting pull requests on GitHub, reporting bugs, suggesting new features, or helping with documentation. Join our community to connect with other contributors.',
      },
      {
        id: 6,
        question: 'How does Zippy Suna protect my privacy?',
        answer:
          'Zippy Suna processes everything on your machine. Your data never leaves your device, ensuring complete privacy and control over your information.',
      },
    ],
  },
  ctaSection: {
    id: 'cta',
    title: 'Start Using Zippy Suna Today',
    backgroundImage: '/holo.png',
    button: {
      text: 'Get Started for free',
      href: '#',
    },
    subtext: 'Experience AI with complete privacy and control',
  },
  footerLinks: [
    {
      title: 'Zippy Suna',
      links: [
        { id: 1, title: 'About', url: 'https://github.com/GoZippy/suna' },
        { id: 3, title: 'Contact', url: 'mailto:admin@localhost' },
        { id: 4, title: 'Documentation', url: 'https://github.com/GoZippy/suna' },
      ],
    },
    {
      title: 'Resources',
      links: [
        {
          id: 5,
          title: 'Documentation',
          url: '#',
        },
        { id: 7, title: 'Community', url: '#' },
        { id: 8, title: 'GitHub', url: '#' },
      ],
    },
    {
      title: 'Legal',
      links: [
        {
          id: 9,
          title: 'Privacy Policy',
          url: '#',
        },
        {
          id: 10,
          title: 'Terms of Service',
          url: '#',
        },
        {
          id: 11,
          title: 'License Apache 2.0',
          url: '#',
        },
      ],
    },
  ],
  useCases: [
    {
      id: 'zippy-chat',
      title: 'Zippy Suna Chat',
      description:
        'Have intelligent conversations with your Zippy Suna AI assistant. All processing happens locally on your machine.',
      category: 'chat',
      featured: true,
      icon: (
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H7L3 21V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ),
      image:
        'https://images.unsplash.com/photo-1576091160550-2173dba999ef?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=2400&q=80',
      url: '#',
    },
    {
      id: 'zippy-writing',
      title: 'Zippy Suna Writing',
      description:
        'Get help with writing, editing, and content creation. Your Zippy Suna AI assistant works locally to help you improve your writing.',
      category: 'writing',
      featured: true,
      icon: (
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M12 4.75L19.25 9L12 13.25L4.75 9L12 4.75Z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M9.25 11.5L4.75 14L12 18.25L19.25 14L14.6722 11.5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ),
      image:
        'https://images.unsplash.com/photo-1444653614773-995cb1ef9efa?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=2400&q=80',
      url: '#',
    },
    {
      id: 'zippy-analysis',
      title: 'Zippy Suna Data Analysis',
      description:
        'Analyze data and get insights from your Zippy Suna AI assistant. All analysis happens locally, keeping your data secure.',
      category: 'analysis',
      featured: true,
      icon: (
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M17.25 10C17.25 12.8995 14.8995 15.25 12 15.25C9.10051 15.25 6.75 12.8995 6.75 10C6.75 7.10051 9.10051 4.75 12 4.75C14.8995 4.75 17.25 7.10051 17.25 10Z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M8.25 14.75L5.25 19.25"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M15.75 14.75L18.75 19.25"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ),
      image:
        'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=2400&q=80',
      url: '#',
    },
  ],
};

export type SiteConfig = typeof siteConfig;
