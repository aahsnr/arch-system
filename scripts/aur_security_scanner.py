#!/usr/bin/env python3
"""
AUR Security Scanner - Enhanced version with improved security and error handling
Analyzes AUR packages for security issues before installation
Requires Python 3.13+
"""

import argparse
import hashlib
import json
import logging
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
import tarfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk levels for security findings"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    
    def __lt__(self, other):
        """Enable sorting by risk level"""
        order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        return order[self.value] < order[other.value]


@dataclass
class SecurityFinding:
    """Represents a security finding with enhanced metadata"""
    risk_level: RiskLevel
    category: str
    description: str
    location: Optional[str] = None
    recommendation: Optional[str] = None
    matched_content: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class AURSecurityError(Exception):
    """Custom exception for AUR security scanner errors"""
    pass


class NetworkManager:
    """Handles all network operations with security controls"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session_headers = {
            'User-Agent': 'AUR-Security-Scanner/1.0 (Python 3.13)',
            'Accept': 'application/json, text/plain',
            'Accept-Encoding': 'gzip, deflate'
        }
    
    def fetch_url(self, url: str, binary: bool = False) -> Union[str, bytes]:
        """Safely fetch URL content with timeout and SSL verification"""
        try:
            # Create SSL context with certificate verification
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            
            request = urllib.request.Request(url, headers=self.session_headers)
            
            with urllib.request.urlopen(request, timeout=self.timeout, context=ssl_context) as response:
                if response.status != 200:
                    raise AURSecurityError(f"HTTP {response.status}: {response.reason}")
                
                content = response.read()
                return content if binary else content.decode('utf-8')
                
        except urllib.error.URLError as e:
            raise AURSecurityError(f"Network error: {e}")
        except ssl.SSLError as e:
            raise AURSecurityError(f"SSL error: {e}")
        except Exception as e:
            raise AURSecurityError(f"Request failed: {e}")


class PKGBUILDAnalyzer:
    """Specialized analyzer for PKGBUILD files"""
    
    # Enhanced suspicious patterns with more context
    SUSPICIOUS_PATTERNS = {
        'network_download_insecure': {
            'pattern': r'(wget|curl|fetch)\s+[^#]*(?:http://|ftp://)[^\s\)]+',
            'risk': RiskLevel.MEDIUM,
            'description': 'Downloads from unencrypted sources (HTTP/FTP)',
            'recommendation': 'Use HTTPS sources when available'
        },
        'shell_execution': {
            'pattern': r'(\$\([^)]*\)|`[^`]*`|eval\s+[^#\n]+|exec\s+[^#\n]+)',
            'risk': RiskLevel.HIGH,
            'description': 'Dynamic shell command execution detected',
            'recommendation': 'Review command execution for potential injection'
        },
        'suspicious_domains': {
            'pattern': r'(pastebin\.com|bit\.ly|tinyurl\.com|t\.co|goo\.gl|raw\.githubusercontent\.com)',
            'risk': RiskLevel.HIGH,
            'description': 'Downloads from URL shorteners or raw content sites',
            'recommendation': 'Verify content authenticity before proceeding'
        },
        'root_operations': {
            'pattern': r'(sudo\s+[^#\n]+|su\s+-[^#\n]*|chmod\s+[0-9]*7[0-9]*|chown\s+root)',
            'risk': RiskLevel.MEDIUM,
            'description': 'Operations requiring elevated privileges',
            'recommendation': 'Ensure operations are necessary and safe'
        },
        'system_modification': {
            'pattern': r'(rm\s+-rf\s+/[^#\n]*|>\s*/etc/[^#\n]*|cp\s+[^#\n]+\s+/etc/)',
            'risk': RiskLevel.CRITICAL,
            'description': 'Direct system file modification detected',
            'recommendation': 'Review system modifications carefully'
        },
        'network_tools': {
            'pattern': r'(nc\s+[^#\n]+|netcat\s+[^#\n]+|nmap\s+[^#\n]+|telnet\s+[^#\n]+)',
            'risk': RiskLevel.MEDIUM,
            'description': 'Network reconnaissance tools usage',
            'recommendation': 'Verify legitimate use of network tools'
        },
        'obfuscation': {
            'pattern': r'(base64\s+-d|echo\s+[A-Za-z0-9+/=]{20,}\s*\||\|sh\s*$|\|bash\s*$)',
            'risk': RiskLevel.HIGH,
            'description': 'Potential code obfuscation or piping to shell',
            'recommendation': 'Decode and review obfuscated content'
        },
        'temp_file_ops': {
            'pattern': r'(>/tmp/[^#\n]*|/tmp/[^#\n]*\|sh|mktemp[^#\n]*\|)',
            'risk': RiskLevel.MEDIUM,
            'description': 'Temporary file operations that could be exploited',
            'recommendation': 'Verify secure temporary file handling'
        }
    }
    
    # Trusted domains for source downloads
    TRUSTED_DOMAINS = {
        'github.com', 'gitlab.com', 'bitbucket.org', 'sourceforge.net',
        'archive.org', 'gnu.org', 'kernel.org', 'python.org', 'mozilla.org',
        'freedesktop.org', 'gnome.org', 'kde.org', 'apache.org', 'debian.org',
        'ubuntu.com', 'fedoraproject.org', 'archlinux.org', 'gentoo.org'
    }
    
    # Required PKGBUILD fields
    REQUIRED_FIELDS = {
        'pkgname': 'Package name identifier',
        'pkgver': 'Package version',
        'pkgrel': 'Package release number',
        'arch': 'Target architectures',
        'license': 'Software license'
    }
    
    # Optional but recommended fields
    RECOMMENDED_FIELDS = {
        'pkgdesc': 'Package description',
        'url': 'Upstream URL',
        'depends': 'Runtime dependencies',
        'makedepends': 'Build dependencies'
    }
    
    def __init__(self):
        self.findings: List[SecurityFinding] = []
    
    def analyze(self, pkgbuild_path: Path) -> List[SecurityFinding]:
        """Analyze PKGBUILD file for security issues"""
        self.findings = []
        
        try:
            content = pkgbuild_path.read_text(encoding='utf-8')
            
            # Core security checks
            self._check_required_fields(content)
            self._check_suspicious_patterns(content, str(pkgbuild_path))
            self._check_source_urls(content)
            self._check_integrity_verification(content)
            self._check_functions(content)
            self._check_variables(content)
            
            return self.findings
            
        except UnicodeDecodeError:
            self.findings.append(SecurityFinding(
                RiskLevel.MEDIUM,
                "Encoding Issue",
                "PKGBUILD contains non-UTF8 characters",
                str(pkgbuild_path),
                "Verify file integrity and encoding"
            ))
        except Exception as e:
            self.findings.append(SecurityFinding(
                RiskLevel.HIGH,
                "Analysis Error",
                f"Failed to analyze PKGBUILD: {str(e)}",
                str(pkgbuild_path)
            ))
        
        return self.findings
    
    def _check_required_fields(self, content: str) -> None:
        """Check if PKGBUILD has required fields"""
        for field, description in self.REQUIRED_FIELDS.items():
            if not re.search(rf'^\s*{field}\s*=', content, re.MULTILINE):
                self.findings.append(SecurityFinding(
                    RiskLevel.HIGH,
                    "Missing Required Field",
                    f"Required field '{field}' ({description}) is missing",
                    recommendation="Add missing required fields to PKGBUILD"
                ))
        
        # Check recommended fields
        missing_recommended = []
        for field, description in self.RECOMMENDED_FIELDS.items():
            if not re.search(rf'^\s*{field}\s*=', content, re.MULTILINE):
                missing_recommended.append(f"{field} ({description})")
        
        if missing_recommended:
            self.findings.append(SecurityFinding(
                RiskLevel.LOW,
                "Missing Recommended Fields",
                f"Recommended fields missing: {', '.join(missing_recommended[:3])}",
                recommendation="Consider adding recommended fields for better package documentation"
            ))
    
    def _check_suspicious_patterns(self, content: str, location: str) -> None:
        """Check for suspicious patterns in content"""
        for pattern_name, pattern_info in self.SUSPICIOUS_PATTERNS.items():
            matches = list(re.finditer(pattern_info['pattern'], content, re.IGNORECASE | re.MULTILINE))
            
            if matches:
                # Get line numbers for better context
                lines = content.split('\n')
                match_details = []
                
                for match in matches[:3]:  # Limit to first 3 matches
                    line_num = content[:match.start()].count('\n') + 1
                    match_details.append(f"Line {line_num}: {match.group().strip()}")
                
                self.findings.append(SecurityFinding(
                    pattern_info['risk'],
                    "Suspicious Pattern",
                    pattern_info['description'],
                    location,
                    pattern_info.get('recommendation'),
                    '; '.join(match_details)
                ))
    
    def _check_source_urls(self, content: str) -> None:
        """Check source URLs for security issues"""
        # Extract source arrays with better regex
        source_pattern = r'source(?:_\w+)?\s*=\s*\((.*?)\)'
        source_matches = re.findall(source_pattern, content, re.DOTALL)
        
        all_urls = []
        for source_block in source_matches:
            # Extract URLs from source block
            url_pattern = r'["\']?(https?://[^"\'\s\)]+)["\']?'
            urls = re.findall(url_pattern, source_block)
            all_urls.extend(urls)
        
        # Also check for direct URL assignments
        direct_url_pattern = r'(?:url|source)\s*=\s*["\']?(https?://[^"\'\s]+)["\']?'
        direct_urls = re.findall(direct_url_pattern, content, re.MULTILINE)
        all_urls.extend(direct_urls)
        
        for url in set(all_urls):  # Remove duplicates
            self._analyze_url(url)
    
    def _analyze_url(self, url: str) -> None:
        """Analyze individual URL for security issues"""
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove port numbers for domain checking
            domain = domain.split(':')[0]
            
            # Check for HTTP (unencrypted)
            if parsed.scheme == 'http':
                self.findings.append(SecurityFinding(
                    RiskLevel.MEDIUM,
                    "Insecure Protocol",
                    f"Unencrypted HTTP download: {domain}",
                    recommendation="Use HTTPS sources when available",
                    matched_content=url
                ))
            
            # Check against trusted domains
            if domain not in self.TRUSTED_DOMAINS:
                # Check for suspicious TLDs
                suspicious_tlds = {'.tk', '.ml', '.ga', '.cf', '.cc'}
                if any(domain.endswith(tld) for tld in suspicious_tlds):
                    risk_level = RiskLevel.HIGH
                    desc = f"Download from suspicious domain: {domain}"
                else:
                    risk_level = RiskLevel.LOW
                    desc = f"Download from non-standard domain: {domain}"
                
                self.findings.append(SecurityFinding(
                    risk_level,
                    "Unknown Source Domain",
                    desc,
                    recommendation="Verify domain reputation and authenticity",
                    matched_content=url
                ))
                
        except Exception as e:
            self.findings.append(SecurityFinding(
                RiskLevel.MEDIUM,
                "URL Parse Error",
                f"Could not parse URL: {url}",
                recommendation="Verify URL format and accessibility"
            ))
    
    def _check_integrity_verification(self, content: str) -> None:
        """Check if package uses integrity verification"""
        checksum_fields = ['md5sums', 'sha1sums', 'sha256sums', 'sha512sums']
        
        found_checksums = []
        for field in checksum_fields:
            if re.search(rf'^\s*{field}\s*=', content, re.MULTILINE):
                found_checksums.append(field)
        
        if not found_checksums:
            self.findings.append(SecurityFinding(
                RiskLevel.HIGH,
                "No Integrity Verification",
                "Package does not verify download integrity with checksums",
                recommendation="Add SHA256 or SHA512 checksums to PKGBUILD"
            ))
        else:
            # Check for weak hash algorithms
            weak_hashes = [h for h in found_checksums if h in ['md5sums', 'sha1sums']]
            if weak_hashes:
                self.findings.append(SecurityFinding(
                    RiskLevel.MEDIUM,
                    "Weak Hash Algorithm",
                    f"Using weak hash algorithms: {', '.join(weak_hashes)}",
                    recommendation="Use SHA256 or SHA512 for better security"
                ))
    
    def _check_functions(self, content: str) -> None:
        """Analyze custom functions in PKGBUILD"""
        # Find function definitions
        function_pattern = r'^\s*(\w+)\s*\(\s*\)\s*\{'
        functions = re.findall(function_pattern, content, re.MULTILINE)
        
        # Standard PKGBUILD functions
        standard_functions = {
            'prepare', 'build', 'check', 'package', 'pkgver'
        }
        
        custom_functions = [f for f in functions if f not in standard_functions]
        if custom_functions:
            self.findings.append(SecurityFinding(
                RiskLevel.LOW,
                "Custom Functions",
                f"PKGBUILD defines custom functions: {', '.join(custom_functions)}",
                recommendation="Review custom function implementations"
            ))
    
    def _check_variables(self, content: str) -> None:
        """Check for suspicious variable usage"""
        # Check for dynamic variable construction
        dynamic_vars = re.findall(r'\$\{[^}]*\$[^}]*\}', content)
        if dynamic_vars:
            self.findings.append(SecurityFinding(
                RiskLevel.MEDIUM,
                "Dynamic Variables",
                f"Dynamic variable construction detected: {dynamic_vars[0]}",
                recommendation="Verify dynamic variable construction is safe"
            ))


class AURSecurityScanner:
    """Main AUR security scanner class with enhanced capabilities"""
    
    def __init__(self, timeout: int = 30):
        self.network = NetworkManager(timeout)
        self.pkgbuild_analyzer = PKGBUILDAnalyzer()
        self.findings: List[SecurityFinding] = []
        self.temp_dir: Optional[Path] = None
    
    @contextmanager
    def _temp_directory(self, prefix: str):
        """Context manager for temporary directory handling"""
        temp_dir = None
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
            yield temp_dir
        finally:
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def scan_package(self, package_name: str) -> Tuple[bool, List[SecurityFinding]]:
        """
        Main method to scan an AUR package with comprehensive security analysis
        
        Args:
            package_name: Name of the AUR package to scan
            
        Returns:
            Tuple of (is_safe, findings_list)
        """
        # Validate package name
        if not self._validate_package_name(package_name):
            return False, [SecurityFinding(
                RiskLevel.CRITICAL,
                "Invalid Package Name",
                f"Package name '{package_name}' contains invalid characters",
                recommendation="Use only alphanumeric characters, hyphens, and underscores"
            )]
        
        self.findings = []
        logger.info(f"Starting security scan for AUR package: {package_name}")
        
        try:
            with self._temp_directory(f"aur-scan-{package_name}-") as temp_dir:
                self.temp_dir = temp_dir
                
                # Step 1: Download and extract package
                package_dir = self._download_and_extract_package(package_name)
                if not package_dir:
                    return False, self.findings
                
                # Step 2: Analyze PKGBUILD
                pkgbuild_path = package_dir / "PKGBUILD"
                if not pkgbuild_path.exists():
                    self.findings.append(SecurityFinding(
                        RiskLevel.CRITICAL,
                        "Missing PKGBUILD",
                        "PKGBUILD file not found in package",
                        recommendation="Package structure is invalid - do not install"
                    ))
                    return False, self.findings
                
                # Run comprehensive analysis
                pkgbuild_findings = self.pkgbuild_analyzer.analyze(pkgbuild_path)
                self.findings.extend(pkgbuild_findings)
                
                # Step 3: Check package metadata
                self._check_package_metadata(package_name)
                
                # Step 4: Analyze additional files
                self._analyze_additional_files(package_dir)
                
                # Step 5: Security assessment
                is_safe = self._assess_overall_security()
                
                logger.info(f"Scan completed for {package_name}. Safe: {is_safe}, Findings: {len(self.findings)}")
                return is_safe, self.findings
                
        except AURSecurityError as e:
            logger.error(f"AUR Security Error: {e}")
            self.findings.append(SecurityFinding(
                RiskLevel.CRITICAL,
                "Security Scanner Error",
                str(e),
                recommendation="Cannot safely analyze package"
            ))
            return False, self.findings
        except Exception as e:
            logger.error(f"Unexpected error scanning {package_name}: {e}")
            self.findings.append(SecurityFinding(
                RiskLevel.CRITICAL,
                "Unexpected Error",
                f"Scanner encountered unexpected error: {str(e)}",
                recommendation="Review package manually or report issue"
            ))
            return False, self.findings
    
    def _validate_package_name(self, package_name: str) -> bool:
        """Validate AUR package name format"""
        # AUR package names should only contain alphanumeric, hyphens, underscores, dots
        if not re.match(r'^[a-zA-Z0-9._+-]+$', package_name):
            return False
        if len(package_name) > 255:  # Reasonable length limit
            return False
        return True
    
    def _download_and_extract_package(self, package_name: str) -> Optional[Path]:
        """Download and safely extract AUR package"""
        try:
            # Download package snapshot
            url = f"https://aur.archlinux.org/cgit/aur.git/snapshot/{package_name}.tar.gz"
            logger.debug(f"Downloading from: {url}")
            
            archive_data = self.network.fetch_url(url, binary=True)
            archive_path = self.temp_dir / f"{package_name}.tar.gz"
            
            with open(archive_path, 'wb') as f:
                f.write(archive_data)
            
            # Safely extract with protection against path traversal
            package_dir = self.temp_dir / package_name
            self._safe_extract_tar(archive_path, self.temp_dir)
            
            if not package_dir.exists():
                raise AURSecurityError(f"Package directory {package_name} not found after extraction")
            
            return package_dir
            
        except AURSecurityError:
            raise
        except Exception as e:
            raise AURSecurityError(f"Failed to download/extract package: {e}")
    
    def _safe_extract_tar(self, archive_path: Path, extract_to: Path) -> None:
        """Safely extract tar archive with path traversal protection"""
        try:
            with tarfile.open(archive_path, 'r:gz') as tar:
                # Check all members for path traversal attempts
                for member in tar.getmembers():
                    # Resolve the path and ensure it's within extract_to
                    member_path = (extract_to / member.name).resolve()
                    if not str(member_path).startswith(str(extract_to.resolve())):
                        raise AURSecurityError(f"Attempted path traversal: {member.name}")
                    
                    # Check for suspicious file sizes (> 100MB)
                    if member.size > 100 * 1024 * 1024:
                        logger.warning(f"Large file in archive: {member.name} ({member.size} bytes)")
                
                # Extract safely
                tar.extractall(path=extract_to, filter='data')
                
        except tarfile.TarError as e:
            raise AURSecurityError(f"Invalid tar archive: {e}")
    
    def _check_package_metadata(self, package_name: str) -> None:
        """Check package information from AUR API"""
        try:
            api_url = f"https://aur.archlinux.org/rpc/?v=5&type=info&arg[]={package_name}"
            response_data = self.network.fetch_url(api_url)
            data = json.loads(response_data)
            
            if data.get('resultcount', 0) == 0:
                self.findings.append(SecurityFinding(
                    RiskLevel.CRITICAL,
                    "Package Not Found",
                    f"Package {package_name} not found in AUR database",
                    recommendation="Verify package name spelling"
                ))
                return
            
            pkg_info = data['results'][0]
            
            # Check maintainer status
            if not pkg_info.get('Maintainer'):
                self.findings.append(SecurityFinding(
                    RiskLevel.HIGH,
                    "Orphaned Package",
                    "Package has no current maintainer",
                    recommendation="Exercise extra caution with orphaned packages"
                ))
            
            # Check package age and update frequency
            last_modified = pkg_info.get('LastModified', 0)
            current_time = time.time()
            days_since_update = (current_time - last_modified) / (24 * 3600)
            
            if days_since_update > 365:
                self.findings.append(SecurityFinding(
                    RiskLevel.MEDIUM,
                    "Outdated Package",
                    f"Package not updated in {int(days_since_update)} days",
                    recommendation="Verify package is still maintained and secure"
                ))
            
            # Check popularity and votes
            popularity = pkg_info.get('Popularity', 0)
            num_votes = pkg_info.get('NumVotes', 0)
            
            if popularity < 0.01 and num_votes < 5:
                self.findings.append(SecurityFinding(
                    RiskLevel.LOW,
                    "Low Adoption",
                    f"Package has low popularity ({popularity:.4f}) and few votes ({num_votes})",
                    recommendation="Verify package necessity and community trust"
                ))
            
            # Check for out-of-date flag
            if pkg_info.get('OutOfDate'):
                self.findings.append(SecurityFinding(
                    RiskLevel.MEDIUM,
                    "Flagged Out of Date",
                    "Package has been flagged as out of date by the community",
                    recommendation="Check for security updates in newer versions"
                ))
                
        except Exception as e:
            logger.warning(f"Could not fetch package metadata: {e}")
            self.findings.append(SecurityFinding(
                RiskLevel.LOW,
                "Metadata Unavailable",
                "Could not retrieve package metadata from AUR",
                recommendation="Manually verify package information"
            ))
    
    def _analyze_additional_files(self, package_dir: Path) -> None:
        """Analyze additional files in package directory"""
        analyzed_files = 0
        
        for file_path in package_dir.rglob('*'):
            if not file_path.is_file() or file_path.name == 'PKGBUILD':
                continue
            
            analyzed_files += 1
            if analyzed_files > 50:  # Limit analysis to prevent DoS
                self.findings.append(SecurityFinding(
                    RiskLevel.LOW,
                    "Many Files",
                    f"Package contains many files (>{analyzed_files-1}), analysis limited",
                    recommendation="Manual review recommended for complex packages"
                ))
                break
            
            try:
                self._analyze_single_file(file_path)
            except Exception as e:
                logger.warning(f"Could not analyze file {file_path}: {e}")
    
    def _analyze_single_file(self, file_path: Path) -> None:
        """Analyze a single file for security issues"""
        file_size = file_path.stat().st_size
        
        # Check for unusually large files
        if file_size > 10 * 1024 * 1024:  # 10MB
            self.findings.append(SecurityFinding(
                RiskLevel.LOW,
                "Large File",
                f"Package contains large file: {file_path.name} ({file_size} bytes)",
                recommendation="Verify large files are necessary"
            ))
        
        # Check file permissions
        file_mode = file_path.stat().st_mode
        if file_mode & 0o111:  # Executable
            self.findings.append(SecurityFinding(
                RiskLevel.MEDIUM,
                "Executable File",
                f"Package contains executable file: {file_path.name}",
                recommendation="Review executable file contents and purpose"
            ))
        
        # Analyze script files
        script_extensions = {'.sh', '.bash', '.zsh', '.py', '.pl', '.rb'}
        if file_path.suffix.lower() in script_extensions:
            try:
                if file_size < 1024 * 1024:  # Only analyze files < 1MB
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    # Run pattern analysis on script content
                    for pattern_name, pattern_info in self.pkgbuild_analyzer.SUSPICIOUS_PATTERNS.items():
                        if re.search(pattern_info['pattern'], content, re.IGNORECASE):
                            self.findings.append(SecurityFinding(
                                pattern_info['risk'],
                                f"Script: {pattern_info['description']}",
                                f"Found in {file_path.name}",
                                str(file_path),
                                pattern_info.get('recommendation')
                            ))
            except (UnicodeDecodeError, OSError):
                pass  # Skip binary or unreadable files
        
        # Check for install files
        if file_path.name.endswith('.install'):
            self.findings.append(SecurityFinding(
                RiskLevel.MEDIUM,
                "Install Script",
                f"Package includes install script: {file_path.name}",
                recommendation="Carefully review install script for post-installation actions"
            ))
    
    def _assess_overall_security(self) -> bool:
        """Assess overall package security based on findings"""
        critical_count = sum(1 for f in self.findings if f.risk_level == RiskLevel.CRITICAL)
        high_count = sum(1 for f in self.findings if f.risk_level == RiskLevel.HIGH)
        medium_count = sum(1 for f in self.findings if f.risk_level == RiskLevel.MEDIUM)
        
        # Package is unsafe if:
        # - Any critical issues
        # - More than 2 high-risk issues
        # - More than 5 medium-risk issues
        if critical_count > 0:
            return False
        if high_count > 2:
            return False
        if medium_count > 5:
            return False
        
        return True
    
    def print_report(self, package_name: str, is_safe: bool, findings: List[SecurityFinding]) -> None:
        """Print comprehensive security scan report"""
        print(f"\n{'='*70}")
        print(f"🔍 AUR Security Scan Report: {package_name}")
        print(f"{'='*70}")
        
        # Overall status
        if is_safe:
            print("✅ PACKAGE APPEARS SAFE TO INSTALL")
        else:
            print("❌ PACKAGE HAS SECURITY CONCERNS - REVIEW REQUIRED")
        
        print(f"\n📊 Summary: {len(findings)} findings")
        
        if not findings:
            print("🎉 No security issues detected!")
            return
        
        # Group findings by risk level
        by_risk = {}
        for finding in findings:
            if finding.risk_level not in by_risk:
                by_risk[finding.risk_level] = []
            by_risk[finding.risk_level].append(finding)
        
        # Print risk level summary
        risk_icons = {
            RiskLevel.CRITICAL: "🚨",
            RiskLevel.HIGH: "⚠️",
            RiskLevel.MEDIUM: "⚡",
            RiskLevel.LOW: "ℹ️"
        }
        
        for risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
            if risk_level in by_risk:
                count = len(by_risk[risk_level])
                icon = risk_icons[risk_level]
                print(f"{icon} {risk_level.value}: {count} finding{'s' if count != 1 else ''}")
        
        # Detailed findings
        print(f"\n📋 Detailed Findings:")
        print("-" * 70)
        
        for risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
            if risk_level not in by_risk:
                continue
                
            print(f"\n{risk_icons[risk_level]} {risk_level.value} RISK FINDINGS:")
            
            for i, finding in enumerate(by_risk[risk_level], 1):
                print(f"\n  {i}. {finding.category}")
                print(f"     Description: {finding.description}")
                
                if finding.location:
                    print(f"     Location: {finding.location}")
                
                if finding.matched_content:
                    # Truncate long matched content
                    content = finding.matched_content
                    if len(content) > 100:
                        content = content[:97] + "..."
                    print(f"     Found: {content}")
                
                if finding.recommendation:
                    print(f"     💡 Recommendation: {finding.recommendation}")
        
        print(f"\n{'='*70}")
        
        if not is_safe:
            print("⚠️  SECURITY ADVISORY:")
            print("   This package has security concerns that should be addressed")
            print("   before installation. Review the findings above and consider:")
            print("   • Contacting the package maintainer about issues")
            print("   • Looking for alternative packages")
            print("   • Manually reviewing the PKGBUILD and source code")
            print("   • Installing in a sandboxed environment for testing")
        else:
            print("✅ This package passed security analysis, but always:")
            print("   • Review the PKGBUILD yourself")
            print("   • Verify source URLs and checksums")  
            print("   • Monitor for updates and security advisories")
        
        print()


class ReportGenerator:
    """Generates various output formats for scan results"""
    
    @staticmethod
    def generate_json_report(results: Dict[str, Dict]) -> str:
        """Generate JSON format report"""
        json_results = {}
        
        for package_name, result in results.items():
            json_results[package_name] = {
                'safe': result['safe'],
                'total_findings': len(result['findings']),
                'risk_summary': ReportGenerator._get_risk_summary(result['findings']),
                'findings': [finding.to_dict() for finding in result['findings']]
            }
        
        return json.dumps(json_results, indent=2, ensure_ascii=False)
    
    @staticmethod
    def generate_summary_report(results: Dict[str, Dict]) -> str:
        """Generate a summary report for multiple packages"""
        report = []
        report.append("AUR Security Scanner - Summary Report")
        report.append("=" * 50)
        
        total_packages = len(results)
        safe_packages = sum(1 for r in results.values() if r['safe'])
        
        report.append(f"Packages scanned: {total_packages}")
        report.append(f"Safe packages: {safe_packages}")
        report.append(f"Packages with concerns: {total_packages - safe_packages}")
        report.append("")
        
        # Per-package summary
        for package_name, result in results.items():
            status = "✅ SAFE" if result['safe'] else "❌ CONCERNS"
            finding_count = len(result['findings'])
            risk_summary = ReportGenerator._get_risk_summary(result['findings'])
            
            report.append(f"{package_name}: {status} ({finding_count} findings)")
            if risk_summary:
                summary_parts = []
                for risk, count in risk_summary.items():
                    if count > 0:
                        summary_parts.append(f"{count} {risk}")
                if summary_parts:
                    report.append(f"  └─ {', '.join(summary_parts)}")
        
        return "\n".join(report)
    
    @staticmethod
    def _get_risk_summary(findings: List[SecurityFinding]) -> Dict[str, int]:
        """Get risk level summary counts"""
        summary = {level.value: 0 for level in RiskLevel}
        for finding in findings:
            summary[finding.risk_level.value] += 1
        return summary


def main():
    """Enhanced main entry point with improved argument handling"""
    parser = argparse.ArgumentParser(
        description="Comprehensive AUR package security scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s yay                          # Scan single package
  %(prog)s yay paru firefox-dev         # Scan multiple packages  
  %(prog)s --json --output report.json yay  # JSON output to file
  %(prog)s --summary --verbose package*     # Summary with verbose logging
  %(prog)s --timeout 60 slow-package       # Custom network timeout
        """
    )
    
    parser.add_argument(
        'packages',
        nargs='+',
        help='AUR package names to scan'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format'
    )
    
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show summary report for multiple packages'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path (default: stdout)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Network timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress non-essential output'
    )
    
    parser.add_argument(
        '--fail-fast',
        action='store_true',
        help='Exit on first unsafe package'
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate arguments
    if args.timeout < 1 or args.timeout > 300:
        print("Error: Timeout must be between 1 and 300 seconds", file=sys.stderr)
        sys.exit(1)
    
    if len(args.packages) > 50:
        print("Error: Too many packages specified (max 50)", file=sys.stderr)
        sys.exit(1)
    
    # Initialize scanner
    scanner = AURSecurityScanner(timeout=args.timeout)
    all_results = {}
    overall_safe = True
    
    # Scan packages
    for i, package_name in enumerate(args.packages, 1):
        if not args.quiet:
            print(f"[{i}/{len(args.packages)}] Scanning {package_name}...", file=sys.stderr)
        
        try:
            is_safe, findings = scanner.scan_package(package_name)
            all_results[package_name] = {
                'safe': is_safe,
                'findings': findings
            }
            
            overall_safe = overall_safe and is_safe
            
            # Fail fast if requested
            if args.fail_fast and not is_safe:
                if not args.quiet:
                    print(f"Package {package_name} failed security check - exiting", file=sys.stderr)
                break
                
        except KeyboardInterrupt:
            print("\nScan interrupted by user", file=sys.stderr)
            sys.exit(130)
        except Exception as e:
            logger.error(f"Failed to scan {package_name}: {e}")
            all_results[package_name] = {
                'safe': False,
                'findings': [SecurityFinding(
                    RiskLevel.CRITICAL,
                    "Scanner Error",
                    f"Failed to complete scan: {str(e)}"
                )]
            }
            overall_safe = False
    
    # Generate output
    try:
        if args.json:
            output_content = ReportGenerator.generate_json_report(all_results)
        elif args.summary and len(args.packages) > 1:
            output_content = ReportGenerator.generate_summary_report(all_results)
        else:
            # Individual package reports
            output_parts = []
            for package_name, result in all_results.items():
                if not args.json and not args.summary:
                    # Use the scanner's print_report method but capture output
                    import io
                    from contextlib import redirect_stdout
                    
                    output_buffer = io.StringIO()
                    with redirect_stdout(output_buffer):
                        scanner.print_report(package_name, result['safe'], result['findings'])
                    output_parts.append(output_buffer.getvalue())
            
            output_content = ''.join(output_parts) if output_parts else ""
        
        # Write output
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_content)
            if not args.quiet:
                print(f"Report written to {args.output}", file=sys.stderr)
        else:
            if args.json or args.summary:
                print(output_content)
            else:
                # For individual reports, they're already printed by print_report
                pass
                
    except IOError as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Final summary for multiple packages
    if len(args.packages) > 1 and not args.json and not args.summary and not args.quiet:
        safe_count = sum(1 for r in all_results.values() if r['safe'])
        total_count = len(all_results)
        
        print(f"\n🏁 Scan Summary: {safe_count}/{total_count} packages passed security check")
        
        if not overall_safe:
            unsafe_packages = [name for name, result in all_results.items() if not result['safe']]
            print(f"⚠️  Packages with concerns: {', '.join(unsafe_packages)}")
    
    # Exit with appropriate code
    sys.exit(0 if overall_safe else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        logger.critical(f"Unexpected error: {e}")
        sys.exit(1)